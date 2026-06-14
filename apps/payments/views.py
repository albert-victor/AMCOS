from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from datetime import timedelta, date
import uuid

from .models import Payment, Invoice, MobilePaymentRequest
from .services import complete_payment, submit_and_auto_verify
from .simulation_helpers import (
    is_pay_simulation_request,
    payment_receipt_json,
    resolve_transaction_id,
)
from .validators import (
    payment_method_other_required,
    payment_method_other_message,
    append_method_specify,
)
from apps.members.models import Member
from apps.core.utils import get_cooperative_id, get_obj_or_404_with_coop, scope_member_queryset
from apps.core.member_utils import get_request_member
from apps.core.permissions import permission_required, access_list_view


def get_cooperative_id(request):
    if request.user.is_authenticated and request.user.role == 'super_admin':
        return None
    return request.session.get('cooperative_id')


def _payment_success_redirect_name(request):
    if getattr(request.user, 'role', None) == 'member':
        return 'core:dashboard'
    return 'payments:list'


# ─── Payment Dashboard ──────────────────────────────────────────────

@permission_required('payments.dashboard')
def payment_dashboard(request):
    cooperative_id = get_cooperative_id(request)
    today = date.today()

    payments = Payment.objects.all()
    if cooperative_id:
        payments = payments.filter(cooperative_id=cooperative_id)

    stats = {
        'total_collected': payments.filter(status='completed').aggregate(t=Sum('amount'))['t'] or 0,
        'pending_count': payments.filter(status='pending').count(),
        'failed_count': payments.filter(status='failed').count(),
        'today_collected': payments.filter(status='completed', payment_date__date=today).aggregate(t=Sum('amount'))['t'] or 0,
        'total_transactions': payments.count(),
        'month_collected': payments.filter(
            status='completed',
            payment_date__month=today.month,
            payment_date__year=today.year,
        ).aggregate(t=Sum('amount'))['t'] or 0,
    }

    recent = payments.order_by('-created_at')[:20]

    payment_type_breakdown = payments.filter(status='completed').values('payment_type').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total')

    payment_method_breakdown = payments.filter(status='completed').values('payment_method').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total')

    return render(request, 'payments/dashboard.html', {
        'stats': stats,
        'recent': recent,
        'type_breakdown': payment_type_breakdown,
        'method_breakdown': payment_method_breakdown,
    })


# ─── Member submits USSD transaction code ──────────────────────────

def _submit_transaction_context(request):
    allowed = {
        'registration_fee', 'membership_fee', 'share_purchase', 'savings_deposit',
        'loan_repayment', 'contribution', 'fine', 'other',
    }
    payment_type = request.GET.get('payment_type', '').strip()
    return {
        'default_payment_type': payment_type if payment_type in allowed else '',
    }


@permission_required('payments.submit')
def payment_submit_transaction(request):
    cooperative_id = get_cooperative_id(request)
    page_context = _submit_transaction_context(request)

    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        payment_method = request.POST.get('payment_method')
        payment_method_other = request.POST.get('payment_method_other', '').strip()
        amount = request.POST.get('amount')
        phone = request.POST.get('phone')
        transaction_id = request.POST.get('transaction_id', '').strip()
        description = request.POST.get('description', '')
        from apps.core.lang import get_request_lang
        lang = get_request_lang(request)

        if not all([payment_type, payment_method, amount, phone]):
            if is_pay_simulation_request(request):
                return JsonResponse({'success': False, 'error': 'Tafadhali jaza sehemu zote / Please fill all fields'}, status=400)
            messages.error(request, 'Tafadhali jaza sehemu zote / Please fill all fields')
            return render(request, 'payments/submit_transaction.html', page_context)

        if not payment_method_other_required(payment_method, payment_method_other):
            err = payment_method_other_message(lang)
            if is_pay_simulation_request(request):
                return JsonResponse({'success': False, 'error': err}, status=400)
            messages.error(request, err)
            return render(request, 'payments/submit_transaction.html', page_context)

        description = append_method_specify(description, payment_method, payment_method_other)
        transaction_id = resolve_transaction_id(transaction_id)

        member = get_request_member(request)
        if request.user.role == 'member' and not member:
            err = 'Akaunti ya mwanachama haijapatikana / Member account not found'
            if is_pay_simulation_request(request):
                return JsonResponse({'success': False, 'error': err}, status=400)
            messages.error(request, err)
            return render(request, 'payments/submit_transaction.html', page_context)

        member_id = member.id if member else None

        payment = Payment.objects.create(
            cooperative_id=cooperative_id,
            member_id=member_id,
            payment_type=payment_type,
            payment_method=payment_method,
            amount=amount,
            reference_number=uuid.uuid4().hex[:12].upper(),
            transaction_id=transaction_id,
            phone=phone,
            description=description,
            status='pending',
            verification_method='auto' if is_pay_simulation_request(request) else 'ussd',
            submitted_at=timezone.now(),
        )

        verified, reason = submit_and_auto_verify(payment)
        payment.refresh_from_db()
        if is_pay_simulation_request(request):
            dest = _payment_success_redirect_name(request)
            return payment_receipt_json(payment, request, {
                'redirect_url': request.build_absolute_uri(reverse(dest)),
                'list_url': request.build_absolute_uri(reverse('payments:list')),
            })

        if verified:
            messages.success(
                request,
                f'Malipo yamethibitishwa kiotomatiki! Rejea: {payment.reference_number}. '
                f'Stakabadhi: {payment.receipt_number}.',
            )
        else:
            messages.success(
                request,
                f'Malipo yamewasilishwa! Namba ya kumbukumbu: {payment.reference_number}. '
                f'Yanasubiri uthibitisho (sababu: {reason}).',
            )
        return redirect('core:dashboard' if request.user.role == 'member' else 'payments:detail', payment_id=payment.id)

    return render(request, 'payments/submit_transaction.html', page_context)


# ─── Payment Verification (Admin confirms with SMS) ────────────────

@permission_required('payments.verify')
def payment_verify(request, payment_id):
    payment = get_obj_or_404_with_coop(Payment, request, payment_id)

    if request.method == 'POST':
        complete_payment(
            payment,
            confirmed_by=request.user.id,
            verification_method=request.POST.get('verification_method', 'manual'),
        )
        payment.refresh_from_db()
        messages.success(request, (
            f'Payment {payment.reference_number} imethibitishwa! '
            f'Receipt: {payment.receipt_number}. SMS imetumwa kwa {payment.phone}.'
        ))
        return redirect('payments:detail', payment_id=payment.id)

    return render(request, 'payments/verify.html', {'payment': payment})


# ─── Existing Views (enhanced) ──────────────────────────────────────

@access_list_view('payments.list', 'payments.list_own')
def payment_list(request):
    cooperative_id = get_cooperative_id(request)
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    method_filter = request.GET.get('method', '')
    search = request.GET.get('q', '')

    payments = Payment.objects.all()
    if cooperative_id:
        payments = payments.filter(cooperative_id=cooperative_id)
    payments = scope_member_queryset(payments, request, 'member_id')
    if status_filter:
        payments = payments.filter(status=status_filter)
    if type_filter:
        payments = payments.filter(payment_type=type_filter)
    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    if search:
        payments = payments.filter(
            Q(reference_number__icontains=search) |
            Q(transaction_id__icontains=search) |
            Q(phone__icontains=search) |
            Q(receipt_number__icontains=search)
        )

    context = {
        'payments': payments[:100],
        'total_collected': payments.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0,
        'pending_count': payments.filter(status='pending').count(),
        'total_count': payments.count(),
    }
    return render(request, 'payments/list.html', context)


@permission_required('payments.make')
def payment_make(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.filter(status='active')
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id)

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        payment_method = request.POST.get('payment_method')
        payment_method_other = request.POST.get('payment_method_other', '').strip()
        from apps.core.lang import get_request_lang
        lang = get_request_lang(request)
        description = request.POST.get('description', '')

        if not payment_method_other_required(payment_method, payment_method_other):
            err = payment_method_other_message(lang)
            if is_pay_simulation_request(request):
                return JsonResponse({'success': False, 'error': err}, status=400)
            messages.error(request, err)
            return render(request, 'payments/make.html', {'members': members})

        phone = request.POST.get('phone', '').strip()
        if not phone:
            err = 'Weka namba ya simu / Enter phone number'
            if is_pay_simulation_request(request):
                return JsonResponse({'success': False, 'error': err}, status=400)
            messages.error(request, err)
            return render(request, 'payments/make.html', {'members': members})

        description = append_method_specify(description, payment_method, payment_method_other)
        transaction_id = resolve_transaction_id(request.POST.get('transaction_id', ''))

        payment = Payment.objects.create(
            cooperative_id=cooperative_id,
            member_id=member_id,
            payment_type=request.POST.get('payment_type'),
            payment_method=payment_method,
            amount=request.POST.get('amount'),
            phone=phone,
            description=description,
            reference_number=uuid.uuid4().hex[:12].upper(),
            transaction_id=transaction_id,
            status='pending',
            submitted_at=timezone.now(),
        )

        if payment_method in ['mpesa', 'tigo_pesa', 'mixx_yas', 'airtel_money', 'halopesa', 'selcom_pesa']:
            MobilePaymentRequest.objects.create(
                cooperative_id=cooperative_id,
                phone=request.POST.get('phone'),
                amount=request.POST.get('amount'),
                provider=payment_method,
                reference=payment.reference_number,
            )
            messages.info(request, f'Payment request sent to {request.POST.get("phone")}')

        if payment_method == 'cash':
            complete_payment(
                payment,
                confirmed_by=request.user.id,
                verification_method='manual',
                send_notification=False,
            )
        else:
            verified, _ = submit_and_auto_verify(payment)
            if verified:
                messages.info(request, 'Malipo yamethibitishwa kiotomatiki.')

        if is_pay_simulation_request(request):
            dest = _payment_success_redirect_name(request)
            return payment_receipt_json(payment, request, {
                'redirect_url': request.build_absolute_uri(reverse(dest)),
                'list_url': request.build_absolute_uri(reverse('payments:list')),
            })

        messages.success(request, f'Payment of {payment.amount} TZS recorded successfully')
        return redirect(_payment_success_redirect_name(request))

    return render(request, 'payments/make.html', {'members': members})


@permission_required('payments.detail')
def payment_detail(request, payment_id):
    payment = get_obj_or_404_with_coop(Payment, request, payment_id)
    return render(request, 'payments/detail.html', {'payment': payment})


@permission_required('payments.verify')
def payment_confirm(request, payment_id):
    return redirect('payments:verify', payment_id=payment_id)


@permission_required('payments.detail')
def payment_receipt(request, payment_id):
    payment = get_obj_or_404_with_coop(Payment, request, payment_id)

    if 'download' in request.GET:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{payment.reference_number}.pdf"'
        response.write(
            render(request, 'payments/receipt.html', {'payment': payment}).content
        )
        return response

    return render(request, 'payments/receipt.html', {'payment': payment})


# ─── Invoice Views ──────────────────────────────────────────────────

@permission_required('payments.invoices')
def invoice_list(request):
    cooperative_id = get_cooperative_id(request)
    status_filter = request.GET.get('status', '')
    invoices = Invoice.objects.all()
    if cooperative_id:
        invoices = invoices.filter(cooperative_id=cooperative_id)
    if status_filter:
        invoices = invoices.filter(invoice_status=status_filter)
    context = {
        'invoices': invoices[:50],
        'total_issued': invoices.filter(invoice_status='issued').aggregate(total=Sum('amount'))['total'] or 0,
        'total_paid': invoices.filter(invoice_status='paid').aggregate(total=Sum('amount'))['total'] or 0,
        'overdue_count': invoices.filter(invoice_status='overdue').count(),
    }
    return render(request, 'payments/invoice_list.html', context)


@permission_required('payments.invoices')
def invoice_detail(request, invoice_id):
    invoice = get_obj_or_404_with_coop(Invoice, request, invoice_id)
    return render(request, 'payments/invoice_detail.html', {'invoice': invoice})


@permission_required('payments.invoices')
def invoice_generate(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.filter(status='active')
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id)

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')
        due_date = request.POST.get('due_date')

        invoice = Invoice.objects.create(
            cooperative_id=cooperative_id,
            member_id=member_id,
            invoice_number=f"INV{cooperative_id:04d}{timezone.now().strftime('%Y%m%d%H%M%S')}",
            amount=amount,
            description=description,
            due_date=due_date or (timezone.now().date() + timedelta(days=30)),
            payer_phone=request.POST.get('payer_phone', ''),
            invoice_status='issued',
        )

        messages.success(request, f'Invoice {invoice.invoice_number} generated. Control Number: {invoice.control_number}')
        return redirect('payments:invoice_detail', invoice_id=invoice.id)

    return render(request, 'payments/invoice_generate.html', {'members': members})


@permission_required('payments.invoices')
def invoice_print(request, invoice_id):
    invoice = get_obj_or_404_with_coop(Invoice, request, invoice_id)
    return render(request, 'payments/invoice_print.html', {'invoice': invoice})


@permission_required('payments.invoices')
def invoice_pay(request, invoice_id):
    cooperative_id = get_cooperative_id(request)
    invoice = get_obj_or_404_with_coop(Invoice, request, invoice_id)
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cash')
        payment = Payment.objects.create(
            cooperative_id=cooperative_id,
            member_id=invoice.member_id,
            payment_type='other',
            payment_method=payment_method,
            amount=invoice.amount,
            reference_number=uuid.uuid4().hex[:12].upper(),
            transaction_id=request.POST.get('transaction_id', ''),
            phone=request.POST.get('phone', ''),
            description=f'Payment for invoice {invoice.invoice_number}',
            status='completed' if payment_method == 'cash' else 'pending',
            payment_date=timezone.now() if payment_method == 'cash' else None,
            confirmed_by=request.user.id if payment_method == 'cash' else None,
            confirmed_at=timezone.now() if payment_method == 'cash' else None,
        )
        payment.receipt_number = f"RCP{payment.id:06d}{timezone.now().strftime('%Y%m%d')}"
        payment.save(update_fields=['receipt_number'])
        invoice.payment = payment
        invoice.is_paid = True
        invoice.invoice_status = 'paid'
        invoice.paid_at = timezone.now()
        invoice.save()
        messages.success(request, f'Invoice {invoice.invoice_number} marked as paid')
        return redirect('payments:invoice_detail', invoice_id=invoice.id)
    return render(request, 'payments/invoice_pay.html', {'invoice': invoice})
