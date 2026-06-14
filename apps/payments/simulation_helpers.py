"""Simulated mobile-money payment (MVP) — no manual TXN entry."""
import random
import string
import uuid

from django.http import JsonResponse
from django.urls import reverse


def generate_simulated_transaction_id():
    chars = string.ascii_uppercase + string.digits
    return 'SIM' + ''.join(random.choices(chars, k=9))


def resolve_transaction_id(post_value):
    tid = (post_value or '').strip()
    if tid:
        return tid
    return generate_simulated_transaction_id()


def is_pay_simulation_request(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.POST.get('pay_simulation') == '1'
    )


def _format_receipt_datetime(dt):
    if not dt:
        return ''
    from django.utils import timezone as tz
    local = tz.localtime(dt) if tz.is_aware(dt) else dt
    return local.strftime('%d/%m/%Y %H:%M')


def payment_receipt_json(payment, request, extra=None):
    from apps.members.models import Member

    member_name = ''
    if payment.member_id:
        member = Member.objects.filter(id=payment.member_id).first()
        if member:
            member_name = member.full_name or member.member_number or ''

    paid_at = payment.payment_date or payment.confirmed_at or payment.created_at

    data = {
        'success': True,
        'payment_id': payment.id,
        'reference_number': payment.reference_number,
        'receipt_number': payment.receipt_number or '',
        'transaction_id': payment.transaction_id or '',
        'amount': str(payment.amount),
        'status': payment.status,
        'phone': payment.phone or '',
        'payment_method': payment.payment_method,
        'payment_method_label': payment.get_payment_method_display(),
        'payment_type_label': payment.get_payment_type_display(),
        'member_name': member_name,
        'paid_at': _format_receipt_datetime(paid_at),
        'org_name': 'MGOWELO AMCOS',
        'receipt_url': request.build_absolute_uri(
            reverse('payments:receipt', args=[payment.id])
        ),
    }
    if extra:
        data.update(extra)
    return JsonResponse(data)
