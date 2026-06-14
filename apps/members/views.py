from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from .models import (
    Member, MemberCategory, NextOfKin, KYCDocument, Beneficiary, CardIssuance,
    MemberBoardApproval, generate_member_id,
)
from .member_access import BOARD_APPROVALS_REQUIRED, board_approval_count
from .services import record_board_approval
from apps.authentication.models import User
from apps.cooperative.models import Cooperative
from apps.core.utils import get_cooperative_id, get_obj_or_404_with_coop, assert_record_access
from apps.core.permissions import role_required, permission_required, access_list_view
from apps.core.lang import get_request_lang
from apps.payments.services import ensure_registration_fee_paid, registration_payment_error_message, normalize_phone
from apps.payments.validators import (
    payment_method_other_required,
    payment_method_other_message,
)
import random
import string
import base64
import io
import json


def generate_member_number(cooperative_id):
    prefix = f"MEM{cooperative_id:04d}"
    while True:
        number = f"{prefix}{random.randint(10000, 99999)}"
        if not Member.objects.filter(member_number=number).exists():
            return number


# ─── Member list, detail, create ────────────────────────────────────

@access_list_view('members.list')
def member_list(request):
    cooperative_id = get_cooperative_id(request)
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    members = Member.objects.all()
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id)
    if query:
        members = members.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(member_number__icontains=query)
        )
    if status_filter:
        members = members.filter(status=status_filter)

    # Annotate card issuance info
    from django.db.models import OuterRef, Subquery
    latest_card = CardIssuance.objects.filter(member=OuterRef('pk')).order_by('-issued_at')
    members = members.annotate(
        last_card_type=Subquery(latest_card.values('card_type')[:1]),
        last_card_date=Subquery(latest_card.values('issued_at')[:1]),
    )

    # Pending approval: those with payment_confirmed or under_review who need ID
    pending_approval = members.filter(status__in=['pending', 'payment_confirmed', 'under_review']).count()

    context = {
        'total_members': members.count(),
        'active_members': members.filter(status='active').count(),
        'pending_members': members.filter(status__in=['pending', 'under_review']).count(),
        'pending_approval': pending_approval,
    }
    members_list = list(members)
    user_ids = [m.user_id for m in members_list if m.user_id]
    users_map = {
        u.id: u
        for u in User.objects.filter(id__in=user_ids).only(
            'id', 'role', 'leadership_role', 'username', 'first_name', 'last_name',
        )
    }
    for m in members_list:
        linked = users_map.get(m.user_id)
        m.linked_user = linked
        m.is_board_leader = bool(
            linked
            and linked.role == 'member'
            and (linked.leadership_role or '') == 'board_member'
        )

    context['members'] = members_list
    context['users_map'] = users_map
    return render(request, 'members/list.html', context)


def _redirect_after_leader_action(request, member):
    if request.POST.get('return') == 'list':
        return redirect('members:list')
    return redirect('members:detail', member_id=member.id)


@login_required
@permission_required('members.promote_leader')
def member_mark_leader(request, member_id):
    if request.method != 'POST':
        return redirect('members:list')
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if not member.user_id:
        messages.error(request, 'Mwanachama hana akaunti ya kuingia. / Member has no login account.')
        return redirect('members:detail', member_id=member.id)
    user = get_object_or_404(User, id=member.user_id)
    if user.role != 'member':
        messages.warning(request, 'Akaunti hii si mwanachama wa kawaida. / This account is not a plain member.')
        return redirect('members:detail', member_id=member.id)
    user.leadership_role = 'board_member'
    user.save(update_fields=['leadership_role'])
    user.refresh_from_db(fields=['leadership_role'])
    from apps.members.services import notify_leadership_elected
    sent = notify_leadership_elected(member, elected_by=request.user)
    messages.success(
        request,
        f'{member.full_name} ameteuliwa mjumbe wa bodi. Arifa imetumwa kwa watumiaji {sent}.',
    )
    return _redirect_after_leader_action(request, member)


@login_required
@permission_required('members.promote_leader')
def member_remove_leader(request, member_id):
    if request.method != 'POST':
        return redirect('members:list')
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if not member.user_id:
        return redirect('members:detail', member_id=member.id)
    user = get_object_or_404(User, id=member.user_id)
    user.leadership_role = ''
    user.save(update_fields=['leadership_role'])
    user.refresh_from_db(fields=['leadership_role'])
    messages.success(request, f'{member.full_name} ameondolewa uongozini.')
    return _redirect_after_leader_action(request, member)


@permission_required('members.detail')
def member_detail(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    issuances = member.card_issuances.all()
    from apps.authentication.models import User
    user_map = {u.id: u.get_full_name() or u.username for u in User.objects.filter(id__in=[i.issued_by for i in issuances])}
    for ci in issuances:
        ci.issued_by_name = user_map.get(ci.issued_by, str(ci.issued_by))
    linked_user = None
    is_board_leader = False
    if member.user_id:
        linked_user = User.objects.filter(id=member.user_id).only(
            'id', 'role', 'leadership_role', 'username', 'first_name', 'last_name',
        ).first()
        is_board_leader = bool(
            linked_user
            and linked_user.role == 'member'
            and (linked_user.leadership_role or '') == 'board_member'
        )
    context = {
        'member': member,
        'linked_user': linked_user,
        'is_board_leader': is_board_leader,
        'documents': member.kyc_documents.all(),
        'beneficiaries': member.beneficiaries.all(),
        'next_of_kins': member.next_of_kins.all(),
        'card_issuances': issuances,
    }
    return render(request, 'members/detail.html', context)


def _member_create_context(request, cooperative_id, categories, title, reg_fee):
    form_data = {}
    if request.method == 'POST':
        form_data = {
            'payment_phone': request.POST.get('payment_phone', ''),
            'payment_reference': request.POST.get('payment_reference', ''),
            'payment_method': request.POST.get('payment_method', ''),
            'first_name': request.POST.get('first_name', ''),
            'last_name': request.POST.get('last_name', ''),
            'phone': request.POST.get('phone', ''),
            'email': request.POST.get('email', ''),
            'national_id': request.POST.get('national_id', ''),
            'gender': request.POST.get('gender', ''),
            'date_of_birth': request.POST.get('date_of_birth', ''),
        }
    return {
        'categories': categories,
        'title': title,
        'reg_fee': reg_fee,
        'form': form_data,
    }


@login_required
@permission_required('members.create')
def member_create(request):
    cooperative_id = get_cooperative_id(request)
    categories = MemberCategory.objects.all()
    if cooperative_id:
        categories = categories.filter(cooperative_id=cooperative_id, status='active')

    cooperative = Cooperative.objects.filter(id=cooperative_id).first() if cooperative_id else None
    reg_fee = (cooperative.registration_fee if cooperative else None) or 100000
    lang = get_request_lang(request)
    title = 'Register New Member'

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')

        payment_method = request.POST.get('payment_method')
        payment_method_other = request.POST.get('payment_method_other', '').strip()
        payment_phone = request.POST.get('payment_phone', '').strip()
        payment_reference = request.POST.get('payment_reference', '').strip()

        ctx = _member_create_context(request, cooperative_id, categories, title, reg_fee)

        if not cooperative_id:
            messages.error(request, registration_payment_error_message('invalid_cooperative', lang))
            return render(request, 'members/form.html', ctx)

        if not payment_method:
            messages.error(
                request,
                'Tafadhali chagua njia ya malipo' if lang != 'en' else 'Please select a payment method',
            )
            return render(request, 'members/form.html', ctx)

        if not payment_method_other_required(payment_method, payment_method_other):
            messages.error(request, payment_method_other_message(lang))
            return render(request, 'members/form.html', ctx)

        if not payment_reference:
            messages.error(
                request,
                'Tafadhali ingiza namba ya kumbukumbu ya malipo'
                if lang != 'en'
                else 'Please enter the payment reference number',
            )
            return render(request, 'members/form.html', ctx)

        if not payment_phone:
            messages.error(
                request,
                'Tafadhali ingiza namba ya simu iliyotumika kulipa'
                if lang != 'en'
                else 'Please enter the phone number used for payment',
            )
            return render(request, 'members/form.html', ctx)

        if not all([first_name, last_name, phone]):
            messages.error(
                request,
                'Tafadhali jaza taarifa za mwanachama'
                if lang != 'en'
                else 'Please fill in member details',
            )
            return render(request, 'members/form.html', ctx)

        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if len(password) < 6:
            messages.error(
                request,
                'Nywila lazima iwe angalau herufi 6' if lang != 'en' else 'Password must be at least 6 characters',
            )
            return render(request, 'members/form.html', ctx)
        if password != confirm_password:
            messages.error(
                request,
                'Nywila hazilingani' if lang != 'en' else 'Passwords do not match',
            )
            return render(request, 'members/form.html', ctx)

        member_phone = normalize_phone(phone) or phone.strip()
        if User.objects.filter(phone=member_phone).exists() or User.objects.filter(username=member_phone).exists():
            messages.error(
                request,
                'Namba ya simu tayari imesajiliwa' if lang != 'en' else 'Phone number is already registered',
            )
            return render(request, 'members/form.html', ctx)

        if national_id and User.objects.filter(national_id=national_id).exists():
            messages.error(
                request,
                'Namba ya kitambulisho tayari imetumika' if lang != 'en' else 'National ID is already in use',
            )
            return render(request, 'members/form.html', ctx)

        payment, pay_reason = ensure_registration_fee_paid(
            cooperative_id=cooperative_id,
            payment_ref=payment_reference,
            payment_method=payment_method,
            payment_method_other=payment_method_other,
            payment_phone=payment_phone,
            payer_description=f'Registration fee (manual) for {first_name} {last_name}',
        )
        if not payment:
            messages.error(request, registration_payment_error_message(pay_reason, lang))
            return render(request, 'members/form.html', ctx)

        with transaction.atomic():
            user = User.objects.create_user(
                username=member_phone,
                phone=member_phone,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                national_id=national_id or None,
                role='member',
                cooperative_id=cooperative_id,
                is_verified=True,
                must_change_password=True,
            )

            member = Member.objects.create(
                cooperative_id=cooperative_id,
                user_id=user.id,
                member_number=generate_member_id(cooperative_id),
                first_name=first_name,
                last_name=last_name,
                phone=member_phone,
                email=email,
                national_id=national_id,
                gender=gender,
                date_of_birth=date_of_birth or None,
                status='payment_confirmed',
                registration_fee_paid=True,
            )
            user.member_id = member.id
            user.save(update_fields=['member_id'])

            payment.member_id = member.id
            payment.save(update_fields=['member_id'])

            if request.POST.get('next_of_kin_name'):
                NextOfKin.objects.create(
                    member=member,
                    full_name=request.POST.get('next_of_kin_name'),
                    relationship=request.POST.get('next_of_kin_relationship'),
                    phone=request.POST.get('next_of_kin_phone'),
                    is_primary=True,
                )

        messages.success(
            request,
            (
                f'Mwanachama {member.member_number} amesajiliwa. Malipo: {payment.reference_number}. '
                f'Akaunti: simu {member_phone} — atalazimika kuweka nywila mpya wakati wa kuingia kwa mara ya kwanza.'
            )
            if lang != 'en'
            else (
                f'Member {member.member_number} registered. Payment ref: {payment.reference_number}. '
                f'Login: phone {member_phone} — they must set a new password on first login.'
            ),
        )
        return redirect('members:detail', member_id=member.id)

    return render(
        request,
        'members/form.html',
        _member_create_context(request, cooperative_id, categories, title, reg_fee),
    )


# ─── Board registration approval (5+ votes) ─────────────────────────

@login_required
@permission_required('members.board_approve')
def pending_registrations(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.filter(
        status__in=['payment_confirmed', 'under_review', 'payment_pending'],
        registration_fee_paid=True,
    ).order_by('-created_at')
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id)
    for m in members:
        m.approval_count = board_approval_count(m)
        m.approvals_needed = max(0, BOARD_APPROVALS_REQUIRED - m.approval_count)
    return render(request, 'members/pending_registrations.html', {
        'members': members,
        'board_required': BOARD_APPROVALS_REQUIRED,
        'page_title': 'Pending Member Registrations',
    })


@login_required
@permission_required('members.board_approve')
def registration_review(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if member.status not in ('payment_confirmed', 'under_review', 'payment_pending', 'approved'):
        messages.info(request, 'This registration is no longer pending board review.')
        return redirect('members:pending_registrations')

    approvals = member.board_approvals.all().order_by('-created_at')
    approver_ids = [a.approver_user_id for a in approvals]
    approvers = {
        u.id: u.get_full_name() or u.username
        for u in User.objects.filter(id__in=approver_ids)
    }
    for a in approvals:
        a.approver_name = approvers.get(a.approver_user_id, str(a.approver_user_id))

    already_voted = MemberBoardApproval.objects.filter(
        member=member,
        approver_user_id=request.user.id,
    ).exists()

    return render(request, 'members/registration_review.html', {
        'member': member,
        'approvals': approvals,
        'approval_count': board_approval_count(member),
        'approvals_needed': max(0, BOARD_APPROVALS_REQUIRED - board_approval_count(member)),
        'board_required': BOARD_APPROVALS_REQUIRED,
        'already_voted': already_voted,
        'page_title': f'Review — {member.full_name}',
    })


@login_required
@permission_required('members.board_approve')
def board_approve_member(request, member_id):
    if request.method != 'POST':
        return redirect('members:registration_review', member_id=member_id)

    member = get_obj_or_404_with_coop(Member, request, member_id)
    if member.status in ('rejected', 'withdrawn', 'active'):
        messages.warning(request, 'Cannot approve this member at current status.')
        return redirect('members:registration_review', member_id=member.id)

    notes = (request.POST.get('notes') or '').strip()
    approval, created = record_board_approval(member, request.user.id, notes)
    member.refresh_from_db()

    if not created:
        messages.info(request, 'You have already approved this member.')
    else:
        messages.success(request, 'Umekubali usajili wa mwanachama.')
    return redirect('members:registration_review', member_id=member.id)


# ─── Approve with auto-generated MGW ID ────────────────────────────

@login_required
@permission_required('members.approve')
def member_approve(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)

    # Auto-generate ID in MGW-YEAR-NNNN format
    new_id = generate_member_id(member.cooperative_id)
    member.member_number = new_id
    member.status = 'active'
    member.is_approved = True
    member.approved_by = request.user.id
    member.approved_at = timezone.now()
    member.save()

    messages.success(request, f'Member {member.full_name} amekubaliwa! Namba yake: {new_id}')
    return redirect('members:detail', member_id=member.id)


@login_required
@permission_required('members.reject')
def member_reject(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if request.method == 'POST':
        member.status = 'rejected'
        member.rejection_reason = request.POST.get('reason', '')
        member.save()
        messages.warning(request, f'Member {member.member_number} rejected')
        return redirect('members:list')
    return render(request, 'members/reject.html', {'member': member})


@login_required
@permission_required('members.suspend')
def member_suspend(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    member.status = 'suspended'
    member.save()
    messages.warning(request, 'Member suspended')
    return redirect('members:detail', member_id=member.id)


@permission_required('members.kyc')
def kyc_documents(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if request.method == 'POST' and request.FILES.get('file'):
        KYCDocument.objects.create(
            member=member,
            document_type=request.POST.get('document_type'),
            document_number=request.POST.get('document_number', ''),
            file=request.FILES['file'],
        )
        messages.success(request, 'Document uploaded successfully')
        return redirect('members:detail', member_id=member.id)
    return render(request, 'members/upload_document.html', {'member': member, 'doc_types': KYCDocument.DOCUMENT_TYPES})


# ─── ID Card Views ─────────────────────────────────────────────────

def generate_qr_base64(data):
    """Return base64 PNG for QR data, or None if qrcode is not installed."""
    try:
        import qrcode
    except ImportError:
        return None
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


@permission_required('members.id_card')
def member_id_card(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    qr_data = f"MGOWELO AMCOS\nID: {member.member_number}\nName: {member.full_name}\nPhone: {member.phone}"
    qr_base64 = generate_qr_base64(qr_data)
    return render(request, 'members/id_card.html', {
        'member': member,
        'qr_base64': qr_base64,
    })


@permission_required('members.id_card')
def member_id_card_pdf(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    from .card_pdf import generate_single_card_pdf
    pdf_buf = generate_single_card_pdf(member)
    response = HttpResponse(pdf_buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ID_{member.member_number}.pdf"'
    return response


DEMO_BULK_CARD_LIMIT = 12


@permission_required('members.id_card_bulk')
def member_id_card_bulk(request):
    cooperative_id = get_cooperative_id(request)
    members_qs = Member.objects.filter(status='active').order_by('member_number')
    if cooperative_id:
        members_qs = members_qs.filter(cooperative_id=cooperative_id)

    total_active = members_qs.count()
    show_all = request.GET.get('all') == '1'
    if show_all:
        limit = min(total_active, 48)
    else:
        limit = min(DEMO_BULK_CARD_LIMIT, total_active)

    cards = []
    for m in members_qs[:limit]:
        qr_data = f"MGOWELO AMCOS\nID: {m.member_number}\nName: {m.full_name}\nPhone: {m.phone}"
        qr_base64 = generate_qr_base64(qr_data)
        cards.append({'member': m, 'qr_base64': qr_base64})

    return render(request, 'members/id_card_bulk.html', {
        'cards': cards,
        'total_active': total_active,
        'shown_count': len(cards),
        'show_all': show_all,
        'demo_limit': DEMO_BULK_CARD_LIMIT,
    })


@permission_required('members.id_card_bulk')
def member_id_card_bulk_pdf(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.filter(status='active').order_by('member_number')
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id)
    from .card_pdf import generate_bulk_cards_pdf
    pdf_buf = generate_bulk_cards_pdf(members)
    response = HttpResponse(pdf_buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="MGOWELO_AMCOS_ID_Cards.pdf"'
    return response


@permission_required('members.kyc')
def member_signature(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if request.method == 'POST':
        data = json.loads(request.body)
        sig_data = data.get('signature', '')
        if sig_data:
            format, imgstr = sig_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f'sig_{member.member_number}.{ext}'
            member.signature.save(file_name, ContentFile(base64.b64decode(imgstr)), save=True)
            return JsonResponse({'status': 'ok', 'url': member.signature.url})
        return JsonResponse({'status': 'error', 'message': 'No signature data'}, status=400)
    return render(request, 'members/signature.html', {'member': member})


@permission_required('members.id_card')
def record_card_issuance(request, member_id):
    member = get_obj_or_404_with_coop(Member, request, member_id)
    if request.method == 'POST':
        card_type = request.POST.get('card_type', 'normal')
        CardIssuance.objects.create(
            member=member,
            card_type=card_type,
            issued_by=request.user.id,
        )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)
