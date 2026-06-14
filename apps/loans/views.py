from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
import random

from .models import LoanProduct, Loan, LoanGuarantor, LoanRepayment, LoanDocument, LoanBoardDecision
from apps.members.models import Member
from apps.shares.models import Share
from apps.cooperative.models import Cooperative
from apps.core.utils import get_cooperative_id, get_obj_or_404_with_coop, scope_member_queryset
from apps.core.permissions import permission_required, access_list_view
from apps.core.dashboard_stats import (
    LOAN_PENDING_STATUSES,
    LOAN_OUTSTANDING_STATUSES,
    LOAN_DISBURSED_STATUSES,
)
from apps.payments.models import Payment
from apps.payments.services import complete_payment


def generate_loan_number(cooperative_id):
    prefix = f"LN{cooperative_id:04d}"
    while True:
        number = f"{prefix}{random.randint(10000, 99999)}"
        if not Loan.objects.filter(loan_number=number).exists():
            return number


def _notify_board_loan_review(cooperative_id, loan):
    """Arifu wanachama wa bodi kuhusu mkopo unaohitaji uamuzi wao."""
    if not cooperative_id:
        return
    from apps.authentication.models import User
    from apps.notifications.models import Notification

    link = f'/loans/{loan.id}/review/'
    title = f'Mkopo {loan.loan_number} unahitaji idhini ya Bodi'
    message = (
        f'Mwanachama amewasilisha mkopo {loan.loan_number} (TZS {loan.amount:,.0f}). '
        f'Fungua ili uapprove au ureject.'
    )
    from apps.authentication.leadership import board_approver_queryset
    for board_user in board_approver_queryset(cooperative_id):
        Notification.objects.create(
            cooperative_id=cooperative_id,
            user_id=board_user.id,
            notification_type='approval',
            priority='normal',
            title=title,
            message=message,
            link=link,
            is_read=False,
            sent_via_email=False,
            sent_via_sms=False,
            sent_via_push=False,
        )


def _ensure_cash_loan_product(cooperative_id):
    """
    Hakikisha kila cooperative ina LoanProduct ya category='cash'.
    Hii inatumika ili "cash special case" iwepo hata kama seed_data haikuunda cash product.
    """
    if not cooperative_id:
        return None

    cash = LoanProduct.objects.filter(
        cooperative_id=cooperative_id,
        category='cash',
        status='active',
    ).first()
    if cash:
        return cash

    coop = Cooperative.objects.filter(id=cooperative_id).first()
    if not coop:
        return None

    cash = LoanProduct.objects.create(
        cooperative_id=cooperative_id,
        name='Cash Loan',
        category='cash',
        description='Cash loans (special case) — board approves/rejects.',
        min_amount=Decimal('1'),
        max_amount=Decimal('999999999999.00'),
        interest_rate=coop.loan_interest_rate,
        interest_method='flat',
        min_duration_months=1,
        max_duration_months=60,
        processing_fee=Decimal('0.00'),
        requires_guarantor=False,
        num_guarantors_required=0,
        status='active',
    )
    return cash


@access_list_view('loans.list', 'loans.list_own')
def loan_list(request):
    cooperative_id = get_cooperative_id(request)
    status_filter = request.GET.get('status', '')

    loans = Loan.objects.all().select_related('product')
    if cooperative_id:
        loans = loans.filter(cooperative_id=cooperative_id)
    loans = scope_member_queryset(loans, request, 'member_id')
    if status_filter:
        loans = loans.filter(status=status_filter)

    context = {
        'loans': loans,
        'total_disbursed': loans.filter(status__in=LOAN_DISBURSED_STATUSES).aggregate(total=Sum('amount'))['total'] or 0,
        'total_outstanding': loans.filter(status__in=LOAN_OUTSTANDING_STATUSES).aggregate(total=Sum('balance'))['total'] or 0,
        'pending_count': loans.filter(status__in=LOAN_PENDING_STATUSES).count(),
    }
    return render(request, 'loans/list.html', context)


@permission_required('loans.detail')
def loan_detail(request, loan_id):
    loan = get_obj_or_404_with_coop(Loan, request, loan_id)
    return render(request, 'loans/detail.html', {
        'loan': loan,
        'repayments': loan.repayments.all()[:20],
        'guarantors': loan.guarantors.all(),
    })


@permission_required('loans.apply')
def loan_apply(request):
    share_unit_price = Decimal('100000')  # Mfumo: hisa 1 = TZS 100,000
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.all()
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id, status='active')
    products = LoanProduct.objects.none()
    if cooperative_id:
        product_list = list(
            LoanProduct.objects.filter(cooperative_id=cooperative_id, status='active'),
        )
        product_list.sort(key=lambda p: (0 if p.category == 'cash' else 1, p.name.lower()))
        products = product_list
    else:
        products = list(LoanProduct.objects.filter(status='active'))
    cooperative = None
    if cooperative_id:
        cooperative = Cooperative.objects.get(id=cooperative_id)
        _ensure_cash_loan_product(cooperative_id)

    share_data = {}
    for m in members:
        try:
            share = Share.objects.get(cooperative_id=cooperative_id, member_id=m.id)
            # Loan cap: cannot exceed total share value (1:1)
            # Mfumo: hisa 1 = TZS 100,000. Tumia total_shares * unit price ili kuondoa tofauti.
            share_value = float(Decimal(share.total_shares) * share_unit_price)
            max_loan = share_value
            share_data[m.id] = {
                'total_shares': share.total_shares,
                'share_value': share_value,
                'max_loan': max_loan,
            }
        except Share.DoesNotExist:
            share_data[m.id] = {
                'total_shares': 0,
                'share_value': 0,
                'max_loan': 0,
            }

    import json
    share_data_json = json.dumps({str(k): v for k, v in share_data.items()})
    default_member_id = None
    if getattr(request.user, 'role', None) == 'member':
        from apps.core.member_utils import get_request_member
        req_member = get_request_member(request)
        if req_member:
            default_member_id = req_member.id

    base_ctx = {
        'members': members,
        'products': products,
        'share_data': share_data,
        'share_data_json': share_data_json,
        'default_member_id': default_member_id,
    }

    if request.method == 'POST':
        member_id = int(request.POST.get('member_id'))
        product_id = request.POST.get('product_id')
        amount = Decimal(request.POST.get('amount', 0))
        duration = int(request.POST.get('duration_months', 1))

        product = get_object_or_404(LoanProduct, id=product_id)

        if amount <= 0:
            messages.error(
                request,
                'Kiasi cha mkopo lazima kiwe zaidi ya sifuri. / Loan amount must be greater than zero.',
            )
            return render(request, 'loans/apply.html', base_ctx)

        sd = share_data.get(member_id, {'max_loan': 0, 'share_value': 0, 'total_shares': 0})
        if sd['total_shares'] <= 0 or sd['share_value'] <= 0:
            messages.error(
                request,
                'Huwezi kuomba mkopo bila hisa. Tafadhali nunua hisa kwanza. / '
                'You cannot apply for a loan without shares. Please purchase shares first.',
            )
            return render(request, 'loans/apply.html', base_ctx)

        share_cap = Decimal(str(sd['share_value']))
        if amount > share_cap:
            messages.error(
                request,
                f'Haiwezekani! Kiasi cha mkopo (TZS {amount:,.0f}) kinazidi thamani ya hisa zako '
                f'(TZS {share_cap:,.0f}). Punguza kiasi au ongeza hisa. / '
                f'Loan amount exceeds your share value (TZS {share_cap:,.0f}). '
                f'Reduce the amount or buy more shares.',
            )
            return render(request, 'loans/apply.html', base_ctx)

        loan = Loan.objects.create(
            cooperative_id=cooperative_id,
            member_id=member_id,
            product=product,
            loan_number=generate_loan_number(cooperative_id),
            amount=amount,
            interest_rate=product.interest_rate,
            interest_method=product.interest_method,
            duration_months=duration,
            processing_fee=product.processing_fee,
            purpose=request.POST.get('purpose', ''),
            # Maombi yote ya wanachama yanaenda moja kwa moja kwa Bodi (under_review).
            status='under_review',
        )
        loan.calculate_installment()
        loan.save()

        from apps.core.models import AuditLog
        AuditLog.objects.create(
            user_id=request.user.id, cooperative_id=cooperative_id,
            action='CREATE', entity_type='Loan', entity_id=loan.id,
            description=f'Loan application {loan.loan_number} submitted for {amount} TZS',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        _notify_board_loan_review(cooperative_id, loan)

        if product.requires_guarantor:
            for i in range(product.num_guarantors_required):
                g_name = request.POST.get(f'guarantor_name_{i}')
                g_phone = request.POST.get(f'guarantor_phone_{i}')
                if g_name and g_phone:
                    LoanGuarantor.objects.create(
                        loan=loan,
                        guarantor_member_id=0,
                        guarantor_name=g_name,
                        guarantor_phone=g_phone,
                        amount=amount * 0.5 if product.num_guarantors_required > 0 else amount,
                    )

        messages.success(request, f'Loan application {loan.loan_number} submitted')
        return redirect('loans:detail', loan_id=loan.id)

    return render(request, 'loans/apply.html', base_ctx)


@permission_required('loans.review')
def loan_review(request, loan_id):
    loan = get_obj_or_404_with_coop(Loan, request, loan_id)
    user_role = request.user.role
    is_secretary = user_role in ['secretary', 'cooperative_admin']
    is_chairman = user_role in ['parrc', 'chairperson', 'cooperative_admin']
    from apps.authentication.leadership import board_approver_queryset, is_board_leader
    is_board = user_role == 'board_member' or is_board_leader(request.user)
    board_member_count = board_approver_queryset(loan.cooperative_id).count()
    board_threshold = min(5, board_member_count) if board_member_count > 0 else 1
    is_cash_loan = bool(getattr(loan, 'product', None)) and loan.product.category == 'cash'

    def _share_cap():
        share_unit_price = Decimal('100000')  # Mfumo: hisa 1 = TZS 100,000
        share = Share.objects.filter(
            cooperative_id=loan.cooperative_id,
            member_id=loan.member_id,
        ).first()
        if not share:
            return Decimal('0')
        return Decimal(share.total_shares) * share_unit_price

    board_approvals_count = LoanBoardDecision.objects.filter(
        loan=loan,
        decision='approve',
    ).count()

    if request.method == 'POST':
        from apps.core.models import AuditLog
        action = request.POST.get('action')
        ip = request.META.get('REMOTE_ADDR', '')

        if action == 'approve':
            if is_board:
                if loan.status not in ['submitted', 'under_review']:
                    messages.error(request, 'Board approval is only allowed while loan is in review.')
                    return redirect('loans:detail', loan_id=loan.id)

                # Normalize legacy cash loans that may still be in "submitted" state.
                if loan.status == 'submitted':
                    loan.status = 'under_review'
                    loan.save(update_fields=['status'])

                share_cap = _share_cap()
                if loan.amount > share_cap:
                    messages.error(
                        request,
                        f'Haiwezekani! Kiasi cha mkopo kinazidi thamani ya hisa zake (TZS {share_cap:,.0f}).',
                    )
                    return redirect('loans:detail', loan_id=loan.id)

                LoanBoardDecision.objects.update_or_create(
                    loan=loan,
                    board_member_user_id=request.user.id,
                    defaults={
                        'decision': 'approve',
                        'reason': request.POST.get('reason', '') or '',
                    },
                )

                board_approvals_count = LoanBoardDecision.objects.filter(
                    loan=loan, decision='approve'
                ).count()

                if board_approvals_count >= board_threshold:
                    loan.status = 'approved'
                    loan.approved_by = request.user.id
                    loan.approved_at = timezone.now()
                    loan.save(update_fields=['status', 'approved_by', 'approved_at'])
                else:
                    # Keep it pending until enough board approvals.
                    loan.reviewed_by = request.user.id
                    loan.reviewed_at = timezone.now()
                    loan.save(update_fields=['reviewed_by', 'reviewed_at'])

                AuditLog.objects.create(
                    user_id=request.user.id,
                    cooperative_id=loan.cooperative_id,
                    action='APPROVE' if loan.status == 'approved' else 'UPDATE',
                    entity_type='Loan',
                    entity_id=loan.id,
                    description=(
                        f'Loan {loan.loan_number} board approve '
                        f'({board_approvals_count}/{board_threshold}) by {user_role}'
                    ),
                    ip_address=ip,
                )
                messages.success(request, 'Board approval recorded')
                return redirect('loans:detail', loan_id=loan.id)

            if is_cash_loan:
                messages.error(request, 'Cash loan requires board approval/rejection only.')
                return redirect('loans:detail', loan_id=loan.id)

            if not (is_secretary or is_chairman):
                messages.error(request, 'You do not have permission to review loans')
                return redirect('loans:detail', loan_id=loan.id)

            if loan.status in ['submitted', 'under_review']:
                if is_chairman:
                    # Chairman can only give final approval after board threshold.
                    if loan.status != 'under_review':
                        messages.error(request, 'Loan must be under review for approval by Chairman.')
                        return redirect('loans:detail', loan_id=loan.id)

                    if board_approvals_count < board_threshold:
                        messages.error(
                            request,
                            f'Bodi bado haijafikia idhini (Board approvals: {board_approvals_count}/{board_threshold}).',
                        )
                        return redirect('loans:detail', loan_id=loan.id)

                    share_cap = _share_cap()
                    if loan.amount > share_cap:
                        messages.error(request, 'Haiwezekani kuidhinisha: mkopo unazidi thamani ya hisa.')
                        return redirect('loans:detail', loan_id=loan.id)

                    loan.status = 'approved'
                    loan.approved_by = request.user.id
                    loan.approved_at = timezone.now()
                else:
                    loan.status = 'under_review'

                loan.reviewed_by = request.user.id
                loan.reviewed_at = timezone.now()
                loan.save()

                AuditLog.objects.create(
                    user_id=request.user.id, cooperative_id=loan.cooperative_id,
                    action='APPROVE' if loan.status == 'approved' else 'UPDATE',
                    entity_type='Loan', entity_id=loan.id,
                    description=f'Loan {loan.loan_number} {"approved" if loan.status == "approved" else "reviewed"} by {user_role}',
                    ip_address=ip,
                )
                messages.success(request, f'Loan {"approved" if loan.status == "approved" else "reviewed and forwarded"}')
            else:
                messages.error(request, f'Loan cannot be reviewed in status: {loan.status}')

        elif action == 'reject':
            rejection_reason = request.POST.get('reason', '') or ''
            if is_board:
                if loan.status not in ['submitted', 'under_review']:
                    messages.error(request, 'Board reject is only allowed while loan is in review.')
                    return redirect('loans:detail', loan_id=loan.id)

                # Normalize legacy cash loans that may still be in "submitted" state.
                if loan.status == 'submitted':
                    loan.status = 'under_review'
                    loan.save(update_fields=['status'])

                LoanBoardDecision.objects.update_or_create(
                    loan=loan,
                    board_member_user_id=request.user.id,
                    defaults={
                        'decision': 'reject',
                        'reason': rejection_reason,
                    },
                )

                loan.status = 'rejected'
                loan.rejection_reason = rejection_reason
                loan.reviewed_by = request.user.id
                loan.reviewed_at = timezone.now()
                loan.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at'])

                AuditLog.objects.create(
                    user_id=request.user.id,
                    cooperative_id=loan.cooperative_id,
                    action='REJECT',
                    entity_type='Loan',
                    entity_id=loan.id,
                    description=f'Loan {loan.loan_number} rejected by board member {user_role}.',
                    ip_address=ip,
                )
                messages.warning(request, 'Loan rejected by board')
                return redirect('loans:detail', loan_id=loan.id)

            if is_cash_loan:
                messages.error(request, 'Cash loan requires board approval/rejection only.')
                return redirect('loans:detail', loan_id=loan.id)

            if not (is_secretary or is_chairman):
                messages.error(request, 'You do not have permission to reject loans')
                return redirect('loans:detail', loan_id=loan.id)

            loan.status = 'rejected'
            loan.rejection_reason = rejection_reason
            loan.reviewed_by = request.user.id
            loan.reviewed_at = timezone.now()
            loan.save()

            AuditLog.objects.create(
                user_id=request.user.id, cooperative_id=loan.cooperative_id,
                action='REJECT', entity_type='Loan', entity_id=loan.id,
                description=f'Loan {loan.loan_number} rejected by {user_role}. Reason: {loan.rejection_reason}',
                ip_address=ip,
            )
            messages.warning(request, 'Loan rejected')

        elif action == 'final_approve':
            if not is_chairman:
                messages.error(request, 'Only the Chairman can give final approval')
                return redirect('loans:detail', loan_id=loan.id)

            if loan.status == 'under_review':
                if is_cash_loan:
                    messages.error(request, 'Cash loans are approved by the board only.')
                    return redirect('loans:detail', loan_id=loan.id)

                board_approvals_count = LoanBoardDecision.objects.filter(
                    loan=loan,
                    decision='approve',
                ).count()
                if board_approvals_count < board_threshold:
                    messages.error(
                        request,
                        f'Loan haiwezi kuidhinishwa: board approvals ni {board_approvals_count}/{board_threshold}.',
                    )
                    return redirect('loans:detail', loan_id=loan.id)

                share_cap = _share_cap()
                if loan.amount > share_cap:
                    messages.error(request, 'Haiwezekani kuidhinisha: mkopo unazidi thamani ya hisa.')
                    return redirect('loans:detail', loan_id=loan.id)

                loan.status = 'approved'
                loan.approved_by = request.user.id
                loan.approved_at = timezone.now()
                loan.save()

                AuditLog.objects.create(
                    user_id=request.user.id, cooperative_id=loan.cooperative_id,
                    action='APPROVE', entity_type='Loan', entity_id=loan.id,
                    description=f'Loan {loan.loan_number} final approved by Chairman',
                    ip_address=ip,
                )
                messages.success(request, 'Loan final approved')
            else:
                messages.error(request, f'Loan must be under_review for final approval (current: {loan.status})')

        return redirect('loans:detail', loan_id=loan.id)

    return render(
        request,
        'loans/review.html',
        {
            'loan': loan,
            'is_secretary': is_secretary,
            'is_chairman': is_chairman,
            'is_board': is_board,
            'is_cash_loan': is_cash_loan,
            'board_approvals_count': board_approvals_count,
            'board_threshold': board_threshold,
        },
    )


@permission_required('loans.disburse')
def loan_disburse(request, loan_id):
    loan = get_obj_or_404_with_coop(Loan, request, loan_id)
    if request.method == 'POST':
        loan.status = 'disbursed'
        loan.disbursed_by = request.user.id
        loan.disbursed_at = timezone.now()
        loan.disbursement_method = request.POST.get('method', 'cash')
        loan.save()
        messages.success(request, f'Loan {loan.loan_number} disbursed')
        return redirect('loans:detail', loan_id=loan.id)
    return render(request, 'loans/disburse.html', {'loan': loan})


@permission_required('loans.repay')
def loan_repayment_create(request, loan_id):
    loan = get_obj_or_404_with_coop(Loan, request, loan_id)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        if amount <= 0:
            messages.error(request, 'Invalid amount')
            return render(request, 'loans/repayment.html', {'loan': loan})

        balance_before = loan.balance
        balance_after = max(0, loan.balance - amount)
        principal_paid = min(amount, loan.balance)
        interest_paid = 0

        LoanRepayment.objects.create(
            loan=loan,
            cooperative_id=loan.cooperative_id,
            member_id=loan.member_id,
            amount=amount,
            principal_paid=principal_paid,
            interest_paid=interest_paid,
            balance_before=balance_before,
            balance_after=balance_after,
            payment_method=request.POST.get('payment_method', 'cash'),
        )

        payment = Payment.objects.create(
            cooperative_id=loan.cooperative_id,
            member_id=loan.member_id,
            payment_type='loan_repayment',
            payment_method=request.POST.get('payment_method', 'cash'),
            amount=amount,
            status='pending',
            submitted_at=timezone.now(),
        )
        complete_payment(
            payment,
            confirmed_by=request.user.id,
            verification_method='manual',
            send_notification=False,
        )

        loan.amount_paid += amount
        loan.balance = balance_after
        if balance_after <= 0:
            loan.status = 'completed'
            loan.completion_date = timezone.now().date()
        loan.save()

        messages.success(request, f'Repayment of {amount} recorded')
        return redirect('loans:detail', loan_id=loan.id)

    return render(request, 'loans/repayment.html', {'loan': loan})


@permission_required('loans.products')
def loan_products(request):
    cooperative_id = get_cooperative_id(request)
    if cooperative_id:
        _ensure_cash_loan_product(cooperative_id)
    products = LoanProduct.objects.all()
    if cooperative_id:
        products = products.filter(cooperative_id=cooperative_id)
    return render(request, 'loans/products.html', {'products': products})


@permission_required('loans.detail')
def loan_schedule(request, loan_id):
    loan = get_obj_or_404_with_coop(Loan, request, loan_id)
    schedule = []
    balance = loan.amount
    installment = loan.monthly_installment

    for i in range(1, loan.duration_months + 1):
        interest = balance * (loan.interest_rate / 100) / 12
        principal = installment - interest
        balance -= principal
        schedule.append({
            'month': i,
            'installment': installment,
            'principal': max(0, principal),
            'interest': max(0, interest),
            'balance': max(0, balance),
        })

    return render(request, 'loans/schedule.html', {'loan': loan, 'schedule': schedule})


@permission_required('loans.detail')
def loan_statement(request, loan_id):
    loan = get_obj_or_404_with_coop(Loan, request, loan_id)
    repayments = loan.repayments.all()[:50]
    return render(request, 'loans/statement.html', {'loan': loan, 'repayments': repayments})
