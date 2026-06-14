import json
import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Share, ShareTransaction, Dividend, DividendPayment
from apps.members.models import Member, generate_member_id
from apps.cooperative.models import Cooperative
from apps.authentication.models import User
from apps.core.utils import get_cooperative_id, get_obj_or_404_with_coop, scope_member_queryset
from apps.core.permissions import permission_required, access_list_view
from apps.payments.models import Payment
from apps.payments.services import complete_payment, submit_and_auto_verify
from apps.payments.validators import (
    payment_method_other_required,
    payment_method_other_message,
    append_method_specify,
)
from apps.payments.simulation_helpers import (
    is_pay_simulation_request,
    payment_receipt_json,
    resolve_transaction_id,
)
from apps.core.dashboard_stats import (
    canonical_share_count,
    resolve_member_for_user,
)
from apps.members.member_access import (
    MAX_INITIAL_SHARES,
    MIN_INITIAL_SHARES,
    activate_full_member_if_shares_paid,
    get_member_lifecycle_stage,
)
from django.urls import reverse


def _resolve_share_txn(transaction_id):
    return resolve_transaction_id(transaction_id)

# Bei rasmi: hisa 1 = TZS 100,000
SHARE_UNIT_PRICE = Decimal('100000')
MAX_SHARE_QUANTITY = 50


def _share_price_for_cooperative(cooperative):
    """Bei ya hisa — hisa 1 = TZS 100,000 (AMCOS)."""
    return SHARE_UNIT_PRICE


def _member_share_snapshot(cooperative_id, members):
    data = {}
    if not cooperative_id:
        return data
    shares = Share.objects.filter(cooperative_id=cooperative_id)
    by_member = {s.member_id: s for s in shares}
    for m in members:
        s = by_member.get(m.id)
        if s:
            data[m.id] = {
                'total_shares': s.total_shares,
                'total_value': float(s.total_value),
            }
        else:
            data[m.id] = {'total_shares': 0, 'total_value': 0}
    return data


def _logged_in_member(request, cooperative_id):
    """Member record for the current user (wanachama)."""
    if not request.user.is_authenticated or getattr(request.user, 'role', None) != 'member':
        return None
    return resolve_member_for_user(request.user, cooperative_id)


def _notify_share_purchased(cooperative_id, beneficiary, purchaser, quantity, total, share_total):
    """Notify beneficiary when someone else buys shares for them."""
    if not beneficiary or not beneficiary.user_id:
        return
    if purchaser.is_authenticated and beneficiary.user_id == purchaser.id:
        return

    buyer = 'Mfanyakazi wa ushirika'
    if purchaser.is_authenticated:
        buyer = purchaser.get_full_name() or purchaser.username or buyer

    from apps.notifications.models import Notification

    Notification.objects.create(
        cooperative_id=cooperative_id,
        user_id=beneficiary.user_id,
        notification_type='payment',
        priority='normal',
        title='Hisa Zimenunuliwa / Shares Purchased',
        message=(
            f'{buyer} amenunua hisa {quantity} kwa niaba yako. '
            f'Jumla: TZS {total:,.0f}. Hisa zako sasa: {share_total}. / '
            f'{buyer} purchased {quantity} share(s) on your behalf. '
            f'Total: TZS {total:,.0f}. Your shares now: {share_total}.'
        ),
        link='/dashboard/',
    )


def _resolve_or_create_member(request, cooperative_id, cooperative):
    member_mode = request.POST.get('member_mode', 'existing')
    from apps.core.lang import get_request_lang
    lang = get_request_lang(request)

    if member_mode == 'new':
        first_name = (request.POST.get('new_first_name') or '').strip()
        last_name = (request.POST.get('new_last_name') or '').strip()
        phone = (request.POST.get('new_phone') or '').strip()
        email = (request.POST.get('new_email') or '').strip()
        national_id = (request.POST.get('new_national_id') or '').strip() or None
        gender = request.POST.get('new_gender') or 'other'

        if not all([first_name, last_name, phone]):
            messages.error(
                request,
                'Jaza jina, jina la ukoo na simu / Fill first name, last name and phone.',
            )
            return None

        if User.objects.filter(phone=phone).exists():
            messages.error(request, 'Namba ya simu tayari imesajiliwa / Phone already registered.')
            return None

        if national_id and User.objects.filter(national_id=national_id).exists():
            messages.error(request, 'NIDA tayari imesajiliwa / National ID already registered.')
            return None

        user = User(
            username=phone,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            email=email,
            national_id=national_id,
            role='member',
            cooperative_id=cooperative_id,
        )
        user.set_unusable_password()
        user.save()

        member = Member.objects.create(
            cooperative_id=cooperative_id,
            user_id=user.id,
            member_number=generate_member_id(cooperative_id),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            national_id=national_id or '',
            gender=gender,
            status='active',
            is_approved=True,
            approved_by=request.user.id,
            approved_at=timezone.now(),
        )
        user.member_id = member.id
        user.save(update_fields=['member_id'])
        return member

    member_id = request.POST.get('member_id')
    if not member_id:
        messages.error(request, 'Chagua mwanachama / Please select a member.')
        return None

    try:
        member = Member.objects.get(id=int(member_id), cooperative_id=cooperative_id)
    except (Member.DoesNotExist, ValueError, TypeError):
        messages.error(request, 'Mwanachama hapatikani / Member not found.')
        return None

    if member.status not in ('active', 'approved', 'payment_confirmed'):
        messages.error(
            request,
            f'Mwanachama hana hali ya kufanya ununuzi (hali: {member.get_status_display()}).',
        )
        return None

    if get_member_lifecycle_stage(member) == 'pending_board':
        messages.error(
            request,
            'Subiri idhini ya bodi (wajumbe 5+) kabla ya kununua hisa. / '
            'Wait for board approval (5+ members) before purchasing shares.',
        )
        return None

    return member


def _record_share_payment(request, cooperative_id, member, total, payment_method,
                          payment_method_other, phone, transaction_id, description, quantity):
    if not payment_method:
        return None

    from apps.core.lang import get_request_lang
    lang = get_request_lang(request)
    if not payment_method_other_required(payment_method, payment_method_other):
        messages.error(request, payment_method_other_message(lang))
        return False

    desc = append_method_specify(
        description or f'Ununuzi wa hisa {quantity} kwa {member.full_name}',
        payment_method,
        payment_method_other,
    )
    payment = Payment.objects.create(
        cooperative_id=cooperative_id,
        member_id=member.id,
        payment_type='share_purchase',
        payment_method=payment_method,
        amount=total,
        phone=phone or member.phone,
        description=desc,
        transaction_id=_resolve_share_txn(transaction_id),
        reference_number=uuid.uuid4().hex[:12].upper(),
        status='pending',
        submitted_at=timezone.now(),
    )
    if payment_method == 'cash':
        complete_payment(
            payment,
            confirmed_by=request.user.id,
            verification_method='manual',
            send_notification=False,
        )
    else:
        submit_and_auto_verify(payment)
    return payment


@access_list_view('shares.list', 'shares.list_own')
def share_list(request):
    cooperative_id = get_cooperative_id(request)
    shares = Share.objects.all()
    if cooperative_id:
        shares = shares.filter(cooperative_id=cooperative_id)
    shares = scope_member_queryset(shares, request, 'member_id')
    member_map = {}
    if cooperative_id:
        mids = [s.member_id for s in shares]
        member_map = {
            m.id: m for m in Member.objects.filter(cooperative_id=cooperative_id, id__in=mids)
        }
    for s in shares:
        s.member_obj = member_map.get(s.member_id)

    # Summary cards must match the rows in the table (member sees own; staff sees coop).
    agg = shares.aggregate(
        total_shares=Sum('total_shares'),
        total_value=Sum('total_value'),
    )
    is_own_view = getattr(request.user, 'role', None) == 'member'
    context = {
        'shares': shares,
        'total_shares': agg['total_shares'] or 0,
        'total_value': agg['total_value'] or 0,
        'stats_for_own_only': is_own_view,
    }
    return render(request, 'shares/list.html', context)


@permission_required('shares.detail')
def share_detail(request, share_id):
    share = get_obj_or_404_with_coop(Share, request, share_id)
    canonical_share_count(share)
    share.refresh_from_db()
    transactions = share.transactions.all()[:50]
    member = Member.objects.filter(
        cooperative_id=share.cooperative_id, id=share.member_id,
    ).first()
    return render(request, 'shares/detail.html', {
        'share': share,
        'transactions': transactions,
        'member': member,
    })


@permission_required('shares.purchase')
def share_purchase(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.all()
    if cooperative_id:
        members = members.filter(
            cooperative_id=cooperative_id,
            status__in=['active', 'payment_confirmed', 'approved'],
        ).order_by('member_number')

    cooperative = None
    if cooperative_id:
        cooperative = Cooperative.objects.filter(id=cooperative_id).first()

    share_price = _share_price_for_cooperative(cooperative)
    share_data = _member_share_snapshot(cooperative_id, members)
    share_data_json = json.dumps({str(k): v for k, v in share_data.items()})

    quantity_options_limited = [1, 2, 3, 4, 5]

    own_member = _logged_in_member(request, cooperative_id)

    base_ctx = {
        'members': members,
        'cooperative': cooperative,
        'share_price': share_price,
        'share_price_int': int(share_price),
        'share_data_json': share_data_json,
        'quantity_options_limited': quantity_options_limited,
        'max_quantity': MAX_SHARE_QUANTITY,
        'own_member': own_member,
    }

    if request.method == 'POST':
        quantity_raw = (request.POST.get('quantity') or '').strip()
        if quantity_raw == 'other':
            try:
                quantity = int(request.POST.get('quantity_custom', 0))
            except (TypeError, ValueError):
                quantity = 0
        else:
            try:
                quantity = int(quantity_raw)
            except (TypeError, ValueError):
                quantity = 0

        own_member = _logged_in_member(request, cooperative_id)
        max_qty = MAX_SHARE_QUANTITY
        if own_member and get_member_lifecycle_stage(own_member) == 'pending_shares':
            max_qty = min(MAX_SHARE_QUANTITY, MAX_INITIAL_SHARES)

        if quantity < MIN_INITIAL_SHARES or quantity > max_qty:
            messages.error(
                request,
                f'Idadi ya hisa lazima iwe kati ya {MIN_INITIAL_SHARES} na {max_qty}.',
            )
            return render(request, 'shares/purchase.html', base_ctx)

        try:
            price_per_share = Decimal(request.POST.get('price_per_share', str(share_price)))
        except InvalidOperation:
            price_per_share = share_price

        if price_per_share != share_price:
            messages.error(request, 'Bei ya hisa si sahihi. Tafadhali jaribu tena.')
            return render(request, 'shares/purchase.html', base_ctx)

        total = price_per_share * quantity
        payment_method = request.POST.get('payment_method', '').strip()
        payment_method_other = request.POST.get('payment_method_other', '').strip()
        phone = request.POST.get('phone', '').strip()
        transaction_id = request.POST.get('transaction_id', '').strip()
        description = request.POST.get('description', '').strip()
        reference = request.POST.get('reference', '').strip()
        pay_result = None

        with transaction.atomic():
            member = _resolve_or_create_member(request, cooperative_id, cooperative)
            if member is None:
                return render(request, 'shares/purchase.html', base_ctx)

            if payment_method:
                pay_result = _record_share_payment(
                    request, cooperative_id, member, total, payment_method,
                    payment_method_other, phone, transaction_id, description, quantity,
                )
                if pay_result is False:
                    return render(request, 'shares/purchase.html', base_ctx)

            share, _created = Share.objects.get_or_create(
                cooperative_id=cooperative_id,
                member_id=member.id,
                defaults={
                    'certificate_number': f"SH{cooperative_id:04d}{member.id:06d}",
                    'total_shares': 0,
                    'total_value': Decimal('0'),
                },
            )

            share.total_shares += quantity
            share.total_value += total
            share.save()
            canonical_share_count(share)
            share.refresh_from_db()

            ShareTransaction.objects.create(
                cooperative_id=cooperative_id,
                member_id=member.id,
                share=share,
                transaction_type='purchase',
                quantity=quantity,
                price_per_share=price_per_share,
                total_amount=total,
                reference=reference or (transaction_id or ''),
                description=description or f'Purchase of {quantity} share(s) @ {price_per_share:,.0f} TZS',
            )

            _notify_share_purchased(
                cooperative_id, member, request.user, quantity, total, share.total_shares,
            )

            activate_full_member_if_shares_paid(member)

        own = _logged_in_member(request, cooperative_id)
        bought_for_self = own is not None and own.id == member.id

        if is_pay_simulation_request(request) and payment_method:
            pay = pay_result if payment_method else None
            if pay:
                if bought_for_self:
                    redirect_to = reverse('core:dashboard')
                else:
                    redirect_to = reverse('shares:detail', args=[share.id])
                extra = {
                    'redirect_url': request.build_absolute_uri(redirect_to),
                    'new_total_shares': share.total_shares,
                    'quantity_purchased': quantity,
                }
                if not bought_for_self:
                    extra['purchased_for'] = member.full_name
                return payment_receipt_json(pay, request, extra)

        messages.success(
            request,
            f'Hisa {quantity} zimenunuliwa kwa {member.full_name} '
            f'({member.member_number}). Jumla: TZS {total:,.0f}',
        )
        if bought_for_self:
            return redirect('core:dashboard')
        return redirect('shares:detail', share_id=share.id)

    return render(request, 'shares/purchase.html', base_ctx)


@permission_required('shares.list')
def dividend_list(request):
    cooperative_id = get_cooperative_id(request)
    dividends = Dividend.objects.all()
    if cooperative_id:
        dividends = dividends.filter(cooperative_id=cooperative_id)
    return render(request, 'shares/dividends.html', {'dividends': dividends})


@permission_required('shares.detail')
def share_certificate(request, share_id):
    share = get_obj_or_404_with_coop(Share, request, share_id)
    cooperative = None
    cid = get_cooperative_id(request)
    if cid:
        cooperative = Cooperative.objects.get(id=cid)
    member = Member.objects.filter(cooperative_id=share.cooperative_id, id=share.member_id).first()
    return render(request, 'shares/certificate.html', {
        'share': share,
        'cooperative': cooperative,
        'member': member,
    })


@permission_required('shares.detail')
def share_receipt(request, share_id):
    share = get_obj_or_404_with_coop(Share, request, share_id)
    cooperative = None
    cid = get_cooperative_id(request)
    if cid:
        cooperative = Cooperative.objects.get(id=cid)
    member = Member.objects.filter(cooperative_id=share.cooperative_id, id=share.member_id).first()
    return render(request, 'shares/certificate.html', {
        'share': share,
        'cooperative': cooperative,
        'member': member,
    })
