from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
import random
import string
import uuid

from django.db import transaction

from .models import User, OTPVerification
from apps.cooperative.models import Cooperative
from apps.payments.models import Payment
from apps.payments.services import submit_and_auto_verify, normalize_phone
from apps.payments.simulation_helpers import resolve_transaction_id
from apps.payments.validators import (
    payment_method_other_required,
    payment_method_other_message,
    append_method_specify,
)
from apps.members.models import Member, generate_member_id
from apps.members.cooperative_defaults import get_mgowelo_cooperative
from apps.members.member_access import parse_hectares_from_post
from apps.members.services import notify_board_new_registration
from apps.notifications.sms_utils import send_sms

logger = logging.getLogger(__name__)


def _phone_lookup_candidates(identifier):
    """Build possible stored phone formats from what user typed."""
    digits = ''.join(c for c in str(identifier or '') if c.isdigit())
    candidates = []
    if digits:
        if digits.startswith('255'):
            candidates.append(digits)
        if digits.startswith('0') and len(digits) > 1:
            candidates.append('255' + digits[1:])
        if len(digits) in (8, 9):
            candidates.append('255' + digits)
    normalized = normalize_phone(identifier)
    if normalized:
        candidates.append(normalized)
    seen = set()
    ordered = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def _normalize_login_identifier(identifier):
    """Common typos / aliases for demo logins."""
    identifier = (identifier or '').strip()
    if not identifier:
        return identifier
    lower = identifier.lower().replace(' ', '')
    if lower.startswith('mcoss'):
        identifier = 'amcos' + identifier[5:]
    aliases = {
        'parrc': 'amcos001_parrc',
        'amcosparrc': 'amcos001_parrc',
        'amcos-parrc': 'amcos001_parrc',
    }
    return aliases.get(lower, identifier)


def resolve_user_by_login_identifier(identifier):
    """Login form accepts phone (UI label) or username."""
    identifier = _normalize_login_identifier(identifier)
    if not identifier:
        return None
    user = User.objects.filter(username__iexact=identifier).first()
    if user:
        return user
    for phone in _phone_lookup_candidates(identifier):
        user = User.objects.filter(phone=phone).first()
        if user:
            return user
        if len(phone) >= 8:
            user = User.objects.filter(phone__endswith=phone[-9:]).first()
            if user:
                return user
            user = User.objects.filter(phone__endswith=phone[-8:]).first()
            if user:
                return user
    return None


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _register_error_response(request, lang, message_sw, message_en, cooperative, reg_fee):
    msg = message_en if lang == 'en' else message_sw
    if _is_ajax(request):
        return JsonResponse({'success': False, 'message': msg}, status=400)
    messages.error(request, msg)
    return render(request, 'auth/register_member.html', {
        'cooperative': cooperative,
        'reg_fee': reg_fee,
    })


def terms_and_conditions(request):
    cooperative = get_mgowelo_cooperative()
    return render(request, 'auth/terms_conditions.html', {
        'cooperative': cooperative,
        'reg_fee': cooperative.registration_fee or 100000,
    })


def register_member(request):
    cooperative = get_mgowelo_cooperative()
    reg_fee = cooperative.registration_fee or 100000

    if request.method == 'POST':
        from apps.core.lang import get_request_lang
        lang = get_request_lang(request)

        if request.POST.get('accept_terms') != '1':
            return _register_error_response(
                request, lang,
                'Lazima ukubali masharti na vigezo vya chama',
                'You must accept the terms and conditions',
                cooperative, reg_fee,
            )

        payment_method = request.POST.get('payment_method')
        payment_method_other = request.POST.get('payment_method_other', '').strip()
        payment_phone = (request.POST.get('payment_phone') or '').strip()

        if not payment_method:
            return _register_error_response(
                request, lang,
                'Tafadhali chagua njia ya malipo',
                'Please select a payment method',
                cooperative, reg_fee,
            )

        if not payment_method_other_required(payment_method, payment_method_other):
            return _register_error_response(
                request, lang,
                payment_method_other_message('sw'),
                payment_method_other_message('en'),
                cooperative, reg_fee,
            )

        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        phone_raw = (request.POST.get('phone') or '').strip()
        email = (request.POST.get('email') or '').strip()
        national_id = (request.POST.get('national_id') or '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        hectares, hectares_note, err_sw, err_en = parse_hectares_from_post(request.POST)
        if err_sw:
            return _register_error_response(request, lang, err_sw, err_en, cooperative, reg_fee)

        if not first_name or not last_name:
            return _register_error_response(
                request, lang, 'Jaza majina kamili', 'Enter your full name', cooperative, reg_fee,
            )

        if not phone_raw:
            return _register_error_response(
                request, lang,
                'Weka namba ya simu ya akaunti yako',
                'Enter your account phone number',
                cooperative, reg_fee,
            )
        if not email:
            return _register_error_response(
                request, lang,
                'Weka barua pepe.',
                'Email is required.',
                cooperative, reg_fee,
            )
        if not national_id:
            return _register_error_response(
                request, lang,
                'Weka NIDA.',
                'National ID is required.',
                cooperative, reg_fee,
            )

        phone = normalize_phone(phone_raw) or phone_raw

        if password != confirm_password:
            return _register_error_response(
                request, lang,
                'Nywila hazifanani. Tafadhali thibitisha nywila yako.',
                'Passwords do not match.',
                cooperative, reg_fee,
            )

        if User.objects.filter(phone=phone).exists() or User.objects.filter(username=phone).exists():
            return _register_error_response(
                request, lang,
                'Namba ya simu tayari imesajiliwa',
                'Phone number already registered',
                cooperative, reg_fee,
            )

        transaction_id = resolve_transaction_id('')

        with transaction.atomic():
            user = User.objects.create_user(
                username=phone,
                phone=phone,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                national_id=national_id or None,
                role='member',
                cooperative_id=cooperative.id,
                is_verified=True,
            )

            member = Member.objects.create(
                cooperative_id=cooperative.id,
                user_id=user.id,
                member_number=generate_member_id(cooperative.id),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email or '',
                national_id=national_id or '',
                gender='other',
                status='payment_pending',
                hectares=hectares,
                hectares_other_note=hectares_note or '',
            )
            user.member_id = member.id
            user.save(update_fields=['member_id'])

            payment = Payment.objects.create(
                cooperative_id=cooperative.id,
                member_id=member.id,
                payment_type='registration_fee',
                payment_method=payment_method,
                amount=reg_fee,
                reference_number=uuid.uuid4().hex[:12].upper(),
                transaction_id=transaction_id,
                phone=payment_phone or phone,
                description=append_method_specify(
                    f'Registration fee — {first_name} {last_name}',
                    payment_method,
                    payment_method_other,
                ),
                status='pending',
                verification_method='auto',
                submitted_at=timezone.now(),
            )

            verified, reason = submit_and_auto_verify(payment)
            if verified:
                member.refresh_from_db()
            else:
                member.status = 'payment_pending'
                member.save(update_fields=['status'])
                return _register_error_response(
                    request, lang,
                    'Malipo hayajathibitishwa. Jaribu tena.',
                    'Payment could not be verified. Please try again.',
                    cooperative, reg_fee,
                )

        notify_board_new_registration(member)

        request.session['registration_fee_paid'] = verified
        request.session['payment_id'] = payment.id
        request.session['member_registration_success'] = {
            'member_number': member.member_number,
            'verified': verified,
            'awaiting_board': True,
        }
        login_url = f"{reverse('auth:login')}?registered=1"
        if _is_ajax(request):
            return JsonResponse({
                'success': True,
                'redirect_url': request.build_absolute_uri(login_url),
                'member_number': member.member_number,
            })
        return redirect(login_url)

    return render(request, 'auth/register_member.html', {
        'cooperative': cooperative,
        'reg_fee': reg_fee,
    })


def _safe_login_redirect(request, default_name='core:dashboard'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        allowed_hosts = {request.get_host(), request.get_host().split(':')[0]}
        if '*' not in settings.ALLOWED_HOSTS:
            allowed_hosts.update(h for h in settings.ALLOWED_HOSTS if h and h != '*')
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts=allowed_hosts,
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
    return redirect(default_name)


def login_view(request):
    if request.user.is_authenticated:
        return _safe_login_redirect(request)

    # After member registration: land once on ?registered=1, then clean URL (avoids CSRF issues on POST)
    if request.method == 'GET' and request.GET.get('registered'):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            flash = request.session.pop('member_registration_success', None)
            if flash:
                request.session['registration_success_flash'] = flash
        return redirect(reverse('auth:login'))

    login_error = False
    account_locked = False
    if request.method == 'POST':
        identifier = (request.POST.get('username') or '').strip()
        password = (request.POST.get('password') or '').strip()
        resolved = resolve_user_by_login_identifier(identifier)
        user = None
        if resolved:
            user = authenticate(request, username=resolved.username, password=password)

        if user is not None:
            if user.is_locked:
                if user.locked_until and user.locked_until > timezone.now():
                    account_locked = True
                    return render(request, 'auth/login.html', {
                        'login_error': False,
                        'account_locked': account_locked,
                    })
                else:
                    user.is_locked = False
                    user.login_attempts = 0
                    user.save()

            login(request, user)
            user.last_login_ip = request.META.get('REMOTE_ADDR')
            user.login_attempts = 0
            user.save(update_fields=['last_login_ip', 'login_attempts'])

            request.session['cooperative_id'] = user.cooperative_id

            if getattr(user, 'must_change_password', False):
                messages.warning(
                    request,
                    'Tafadhali weka nywila mpya kabla ya kuendelea / Please reset your password before continuing.',
                )
                return redirect('auth:force_password_change')

            messages.success(request, f'Welcome back, {user.get_full_name()}!')

            if user.role == 'super_admin':
                return _safe_login_redirect(request, 'core:super_admin_dashboard')
            return _safe_login_redirect(request)
        else:
            if resolved:
                resolved.login_attempts += 1
                if resolved.login_attempts >= 5:
                    resolved.is_locked = True
                    resolved.locked_until = timezone.now() + timedelta(minutes=30)
                resolved.save(
                    update_fields=['login_attempts', 'is_locked', 'locked_until']
                )
            login_error = True

    registration_success = request.session.pop('registration_success_flash', None)
    return render(request, 'auth/login.html', {
        'registration_success': registration_success,
        'login_error': login_error,
        'account_locked': account_locked,
    })


@login_required
def user_profile(request):
    """Edit own user account (not cooperative settings)."""
    user = request.user
    from apps.core.member_utils import resolve_member_for_user
    cooperative_id = request.session.get('cooperative_id') or user.cooperative_id
    member = resolve_member_for_user(user, cooperative_id)

    if request.method == 'POST':
        user.first_name = (request.POST.get('first_name') or user.first_name or '').strip()
        user.last_name = (request.POST.get('last_name') or user.last_name or '').strip()
        email = (request.POST.get('email') or '').strip()
        if email:
            user.email = email
        user.address = (request.POST.get('address') or '').strip()
        user.city = (request.POST.get('city') or '').strip()
        user.region = (request.POST.get('region') or '').strip()
        if request.FILES.get('profile_image'):
            user.profile_image = request.FILES['profile_image']
        user.save()

        if member:
            member.email = email or member.email
            member.address = user.address or member.address
            member.city = user.city or member.city
            member.region = user.region or member.region
            if request.FILES.get('profile_image'):
                member.profile_image = request.FILES['profile_image']
            member.save()

        messages.success(request, 'Wasifu wako umesasishwa.')
        return redirect('auth:profile')

    return render(request, 'auth/profile.html', {
        'profile_user': user,
        'member': member,
        'leadership_role': getattr(user, 'leadership_role', ''),
    })


@login_required
def force_password_change(request):
    """Mandatory password reset for users registered by cooperative admin."""
    user = request.user
    if not getattr(user, 'must_change_password', False):
        if user.role == 'super_admin':
            return redirect('core:super_admin_dashboard')
        return redirect('core:dashboard')

    from apps.core.lang import get_request_lang
    lang = get_request_lang(request)

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(new_password) < 6:
            messages.error(
                request,
                'Nywila lazima iwe angalau herufi 6' if lang != 'en' else 'Password must be at least 6 characters',
            )
            return render(request, 'auth/force_password_change.html')

        if new_password != confirm_password:
            messages.error(
                request,
                'Nywila hazilingani' if lang != 'en' else 'Passwords do not match',
            )
            return render(request, 'auth/force_password_change.html')

        if user.check_password(new_password):
            messages.error(
                request,
                'Tumia nywila tofauti na ile uliyopewa na ofisi'
                if lang != 'en'
                else 'Choose a different password than the temporary one from the office',
            )
            return render(request, 'auth/force_password_change.html')

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        update_session_auth_hash(request, user)
        messages.success(
            request,
            'Nywila imewekwa. Karibu MGOWELO AMCOS!'
            if lang != 'en'
            else 'Password updated. Welcome to MGOWELO AMCOS!',
        )
        if user.role == 'super_admin':
            return redirect('core:super_admin_dashboard')
        return redirect('core:dashboard')

    return render(request, 'auth/force_password_change.html')


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('auth:login')


def password_reset_request(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        try:
            user = User.objects.get(phone=phone)
            otp = generate_otp()
            OTPVerification.objects.create(
                phone=phone,
                otp_code=otp,
                otp_type='password_reset',
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            request.session['reset_user_id'] = user.id
            messages.success(request, 'OTP sent for password reset')
            return redirect('auth:password_reset_verify')
        except User.DoesNotExist:
            messages.error(request, 'Phone number not registered')
    return render(request, 'auth/password_reset.html')


def password_reset_verify(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('auth:password_reset')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'auth/password_reset_verify.html')

        try:
            user = User.objects.get(id=user_id)
            otp = OTPVerification.objects.filter(
                phone=user.phone, otp_code=otp_code, otp_type='password_reset', is_used=False
            ).latest('created_at')

            if otp.expires_at < timezone.now():
                messages.error(request, 'OTP has expired')
                return render(request, 'auth/password_reset_verify.html')

            otp.is_used = True
            otp.save()
            user.set_password(new_password)
            user.save()
            del request.session['reset_user_id']
            messages.success(request, 'Password reset successful')
            return redirect('home')
        except Exception:
            messages.error(request, 'Invalid OTP')

    return render(request, 'auth/password_reset_verify.html')
