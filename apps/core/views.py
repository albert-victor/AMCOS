from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.core.db_resilience import read_db_status, test_django_connection, mysql_ping
from apps.cooperative.models import Cooperative
from apps.members.models import Member, CardIssuance
from apps.savings.models import SavingsAccount
from apps.loans.models import Loan, LoanRepayment
from apps.payments.models import Payment
from apps.shares.models import Share
from apps.governance.models import Meeting, Election, Resolution
from apps.core.models import SystemSetting
from apps.core.dashboard_stats import (
    cooperative_totals,
    member_totals,
    resolve_member_for_user,
    LOAN_PENDING_STATUSES,
    LOAN_ACTIVE_STATUSES,
    LOAN_OUTSTANDING_STATUSES,
    LOAN_DISBURSED_STATUSES,
)
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta


def welcome(request):
    if request.user.is_authenticated:
        if request.user.role == 'super_admin':
            return redirect('core:super_admin_dashboard')
        return redirect('core:dashboard')
    return render(request, 'dashboard/welcome.html')


def set_language_view(request):
    from apps.core.lang import normalize_lang
    lang = normalize_lang(request.GET.get('lang'))
    request.session['lang'] = lang
    request.session.modified = True
    response = redirect(request.GET.get('next', '/'))
    max_age = 365 * 24 * 60 * 60
    response.set_cookie('django_language', lang, max_age=max_age)
    return response


@login_required
def dashboard(request):
    user = request.user
    role = user.role

    if role == 'super_admin':
        return redirect('core:super_admin_dashboard')

    cooperative_id = request.session.get('cooperative_id')
    base_ctx = {'role': role, 'user': user}

    from apps.authentication.leadership import (
        CHAIR_DASHBOARD_ROLES, SECRETARY_DASHBOARD_ROLES, TCDC_DASHBOARD_ROLES, is_board_leader,
    )

    if role in CHAIR_DASHBOARD_ROLES:
        return chairperson_dashboard(request, cooperative_id, base_ctx)
    elif role in SECRETARY_DASHBOARD_ROLES:
        return secretary_dashboard(request, cooperative_id, base_ctx)
    elif role == 'treasurer':
        return treasurer_dashboard(request, cooperative_id, base_ctx)
    elif role == 'accountant':
        return accountant_dashboard(request, cooperative_id, base_ctx)
    elif role == 'board_member':
        return board_dashboard(request, cooperative_id, base_ctx)
    elif role == 'carder':
        return carder_dashboard(request, cooperative_id, base_ctx)
    elif role == 'loan_officer':
        return loan_officer_dashboard(request, cooperative_id, base_ctx)
    elif role == 'auditor':
        return auditor_dashboard(request, cooperative_id, base_ctx)
    elif role in TCDC_DASHBOARD_ROLES:
        return tcdc_dashboard(request, cooperative_id, base_ctx)
    elif role == 'member':
        return member_dashboard(request, cooperative_id, base_ctx, user, is_board_leader=is_board_leader(user))
    elif role == 'cooperative_admin':
        return cooperative_admin_dashboard(request, cooperative_id, base_ctx)
    else:
        return cooperative_admin_dashboard(request, cooperative_id, base_ctx)


def chairperson_dashboard(request, cooperative_id, base_ctx):
    stats = cooperative_totals(cooperative_id)
    ctx = {
        **base_ctx,
        **stats,
        'upcoming_meetings': Meeting.objects.filter(cooperative_id=cooperative_id, status__in=['scheduled', 'in_progress'])[:5],
        'total_meetings': Meeting.objects.filter(cooperative_id=cooperative_id).count(),
        'active_elections': Election.objects.filter(cooperative_id=cooperative_id, status__in=['nomination', 'campaign', 'voting']).count(),
        'resolutions_pending': Resolution.objects.filter(meeting__cooperative_id=cooperative_id, implemented=False).count(),
        'recent_payments': Payment.objects.filter(cooperative_id=cooperative_id).order_by('-created_at')[:5],
        'recent_members': Member.objects.filter(cooperative_id=cooperative_id).order_by('-created_at')[:5],
        'page_title': 'PA-RC Dashboard' if base_ctx.get('role') == 'parrc' else 'Mwenyekiti Dashboard',
    }
    return render(request, 'dashboard/chairperson.html', ctx)


def secretary_dashboard(request, cooperative_id, base_ctx):
    stats = cooperative_totals(cooperative_id)
    ctx = {
        **base_ctx,
        **stats,
        'total_members': stats['total_members_all'],
        'total_meetings': Meeting.objects.filter(cooperative_id=cooperative_id).count(),
        'upcoming_meetings': Meeting.objects.filter(cooperative_id=cooperative_id, status__in=['scheduled', 'in_progress']).count(),
        'recent_applications': Member.objects.filter(cooperative_id=cooperative_id, status__in=['submitted', 'pending', 'under_review'])[:10],
        'recent_meetings': Meeting.objects.filter(cooperative_id=cooperative_id)[:5],
        'page_title': 'Katibu Dashboard',
    }
    return render(request, 'dashboard/secretary.html', ctx)


def treasurer_dashboard(request, cooperative_id, base_ctx):
    stats = cooperative_totals(cooperative_id)
    ctx = {
        **base_ctx,
        **stats,
        'recent_payments': Payment.objects.filter(cooperative_id=cooperative_id)[:10],
        'active_loans_count': stats['active_loans'],
        'page_title': 'Mhazini Dashboard',
    }
    return render(request, 'dashboard/treasurer.html', ctx)


def accountant_dashboard(request, cooperative_id, base_ctx):
    stats = cooperative_totals(cooperative_id)
    total_income = stats['total_payments']
    total_expenses = 0
    total_budget = 0
    try:
        from apps.accounting.models import Expense, Budget
        total_expenses = Expense.objects.filter(cooperative_id=cooperative_id).aggregate(total=Sum('amount'))['total'] or 0
        total_budget = Budget.objects.filter(cooperative_id=cooperative_id).aggregate(total=Sum('amount'))['total'] or 0
    except Exception:
        pass
    pending_payments = Payment.objects.filter(
        cooperative_id=cooperative_id, status='pending',
    ).count()
    ctx = {
        **base_ctx,
        **stats,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': total_income - total_expenses,
        'total_budget': total_budget,
        'recent_transactions': Payment.objects.filter(cooperative_id=cooperative_id, status='completed')[:10],
        'pending_payments': pending_payments,
        'page_title': 'Mhasibu Dashboard',
    }
    return render(request, 'dashboard/accountant.html', ctx)


def board_dashboard(request, cooperative_id, base_ctx):
    from apps.members.member_access import BOARD_APPROVALS_REQUIRED
    pending_registrations = Member.objects.filter(
        cooperative_id=cooperative_id,
        status__in=['payment_confirmed', 'under_review', 'payment_pending'],
        registration_fee_paid=True,
    ).count() if cooperative_id else 0

    stats = cooperative_totals(cooperative_id)
    total_income = stats['total_payments']
    total_expenses = 0
    total_budget = 0
    try:
        from apps.accounting.models import Expense, Budget
        total_expenses = Expense.objects.filter(cooperative_id=cooperative_id).aggregate(total=Sum('amount'))['total'] or 0
        total_budget = Budget.objects.filter(cooperative_id=cooperative_id).aggregate(total=Sum('amount'))['total'] or 0
    except Exception:
        pass

    pending_loans_qs = Loan.objects.filter(
        cooperative_id=cooperative_id,
        status__in=LOAN_PENDING_STATUSES,
    ).select_related('product').order_by('-created_at')
    pending_board_review = pending_loans_qs.count()

    ctx = {
        **base_ctx,
        **stats,
        'pending_board_review': pending_board_review,
        'pending_loan_applications': pending_loans_qs[:10],
        'total_meetings': Meeting.objects.filter(cooperative_id=cooperative_id).count(),
        'upcoming_meetings': Meeting.objects.filter(cooperative_id=cooperative_id, status__in=['scheduled', 'in_progress']).count(),
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_budget': total_budget,
        'active_elections': Election.objects.filter(cooperative_id=cooperative_id, status__in=['nomination', 'campaign', 'voting']).count(),
        'recent_payments': Payment.objects.filter(cooperative_id=cooperative_id)[:5],
        'pending_registrations': pending_registrations,
        'board_approvals_required': BOARD_APPROVALS_REQUIRED,
        'page_title': 'Bodi ya Uongozi Dashboard',
    }
    return render(request, 'dashboard/board.html', ctx)


def loan_officer_dashboard(request, cooperative_id, base_ctx):
    stats = cooperative_totals(cooperative_id)
    loans_qs = Loan.objects.filter(cooperative_id=cooperative_id)
    ctx = {
        **base_ctx,
        'pending_review': loans_qs.filter(status__in=LOAN_PENDING_STATUSES).count(),
        'approved_awaiting': loans_qs.filter(status='approved').count(),
        'active_loans': stats['active_loans'],
        'total_disbursed': stats['total_disbursed'],
        'recent_loans': loans_qs.order_by('-created_at')[:8],
        'page_title': 'Afisa Mikopo Dashboard',
    }
    return render(request, 'dashboard/loan_officer.html', ctx)


def auditor_dashboard(request, cooperative_id, base_ctx):
    pending_audits = 0
    open_fraud = 0
    try:
        from apps.audit.models import AuditTrail, FraudAlert
        pending_audits = AuditTrail.objects.filter(cooperative_id=cooperative_id).count()
        open_fraud = FraudAlert.objects.filter(
            cooperative_id=cooperative_id, status='open'
        ).count()
    except Exception:
        pass
    ctx = {
        **base_ctx,
        'audit_entries': pending_audits,
        'open_fraud_alerts': open_fraud,
        'total_members': Member.objects.filter(cooperative_id=cooperative_id).count(),
        'recent_payments': Payment.objects.filter(cooperative_id=cooperative_id).order_by('-created_at')[:8],
        'page_title': 'Mkaguzi Dashboard',
    }
    return render(request, 'dashboard/auditor.html', ctx)


def tcdc_dashboard(request, cooperative_id, base_ctx):
    """Tume ya Maendeleo ya Ushirika — read-only oversight dashboard (wilaya / mkoa)."""
    stats = cooperative_totals(cooperative_id)
    audit_entries = 0
    open_fraud = 0
    try:
        from apps.audit.models import AuditTrail, FraudAlert
        audit_entries = AuditTrail.objects.filter(cooperative_id=cooperative_id).count()
        open_fraud = FraudAlert.objects.filter(
            cooperative_id=cooperative_id, status='open'
        ).count()
    except Exception:
        pass
    level_sw = 'Wilaya' if base_ctx.get('role') == 'tcdc_wilaya' else 'Mkoa'
    level_en = 'District' if base_ctx.get('role') == 'tcdc_wilaya' else 'Regional'
    ctx = {
        **base_ctx,
        **stats,
        'audit_entries': audit_entries,
        'open_fraud_alerts': open_fraud,
        'recent_payments': Payment.objects.filter(cooperative_id=cooperative_id).order_by('-created_at')[:8],
        'recent_members': Member.objects.filter(cooperative_id=cooperative_id).order_by('-created_at')[:5],
        'level_sw': level_sw,
        'level_en': level_en,
        'page_title': f'TCDC Dashboard ({level_en})',
    }
    return render(request, 'dashboard/tcdc.html', ctx)


def carder_dashboard(request, cooperative_id, base_ctx):
    now = timezone.now()
    total_members = Member.objects.filter(cooperative_id=cooperative_id).count()
    active_members = Member.objects.filter(cooperative_id=cooperative_id, status='active').count()
    pending_members = Member.objects.filter(cooperative_id=cooperative_id, status__in=['pending', 'under_review', 'payment_confirmed']).count()
    cards_issued = CardIssuance.objects.filter(member__cooperative_id=cooperative_id).count()
    recent_members = Member.objects.filter(cooperative_id=cooperative_id).order_by('-created_at')[:5]
    recent_cards = CardIssuance.objects.filter(member__cooperative_id=cooperative_id).select_related('member').order_by('-issued_at')[:5]
    ctx = {
        **base_ctx,
        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,
        'cards_issued': cards_issued,
        'recent_members': recent_members,
        'recent_cards': recent_cards,
        'page_title': 'Carder Dashboard',
    }
    return render(request, 'dashboard/carder.html', ctx)


def member_dashboard(request, cooperative_id, base_ctx, user, is_board_leader=False):
    from apps.members.member_access import (
        BOARD_APPROVALS_REQUIRED,
        board_approval_count,
        get_member_lifecycle_stage,
        is_restricted_member,
    )
    member = resolve_member_for_user(user, cooperative_id)
    mstats = member_totals(cooperative_id, member)
    lifecycle = get_member_lifecycle_stage(member) if member else None
    pending_registrations = 0
    if is_board_leader and cooperative_id:
        pending_registrations = Member.objects.filter(
            cooperative_id=cooperative_id,
            status__in=['payment_confirmed', 'under_review', 'payment_pending'],
            registration_fee_paid=True,
        ).count()
    ctx = {
        **base_ctx,
        'member': member,
        **mstats,
        'member_lifecycle_stage': lifecycle,
        'member_is_restricted': is_restricted_member(member) if member else False,
        'member_board_approvals': board_approval_count(member) if member else 0,
        'member_board_required': BOARD_APPROVALS_REQUIRED,
        'is_board_leader': is_board_leader,
        'pending_registrations': pending_registrations,
        'total_meetings': Meeting.objects.filter(cooperative_id=cooperative_id).count(),
        'active_elections': Election.objects.filter(cooperative_id=cooperative_id, status__in=['nomination', 'campaign', 'voting']).count(),
        'page_title': 'Mwanachama Dashboard',
    }
    return render(request, 'dashboard/member.html', ctx)


def cooperative_admin_dashboard(request, cooperative_id, base_ctx):
    stats = cooperative_totals(cooperative_id)
    ctx = {
        **base_ctx,
        **stats,
        'recent_payments': Payment.objects.filter(cooperative_id=cooperative_id)[:10],
        'recent_members': Member.objects.filter(cooperative_id=cooperative_id)[:10],
    }
    return render(request, 'dashboard/index.html', ctx)


@staff_member_required
def super_admin_dashboard(request):
    context = {
        'total_cooperatives': Cooperative.objects.count(),
        'active_cooperatives': Cooperative.objects.filter(status='active').count(),
        'total_members': Member.objects.count(),
        'total_revenue': Payment.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'cooperatives': Cooperative.objects.all()[:20],
    }
    return render(request, 'dashboard/super_admin.html', context)


@staff_member_required
def system_settings(request):
    if request.method == 'POST':
        settings_map = {
            'site_name': 'MGOWELO AMCOS',
            'site_address': '',
            'site_phone': '',
            'site_email': '',
            'site_currency': 'TZS',
            'email_host': 'smtp.gmail.com',
            'email_port': '587',
            'email_host_user': '',
            'email_host_password': '',
            'email_use_tls': 'True',
            'sms_api_key': '',
            'sms_sender_id': 'MKUUWA',
            'mpesa_consumer_key': '',
            'mpesa_consumer_secret': '',
            'mpesa_passkey': '',
            'mpesa_shortcode': '',
            'mpesa_environment': 'sandbox',
            'tigo_api_key': '',
            'airtel_api_key': '',
            'loan_interest_rate': '12',
            'loan_max_amount': '10000000',
            'loan_max_duration_months': '24',
            'savings_interest_rate': '3',
        }
        for key, default in settings_map.items():
            val = request.POST.get(key, '').strip()
            if key == 'email_use_tls':
                val = 'True' if request.POST.get(key) == 'on' else 'False'
            obj, _ = SystemSetting.objects.get_or_create(key=key)
            obj.value = val if val else default
            obj.save()
        messages.success(request, 'Mipangilio imehifadhiwa / Settings saved successfully')
        return redirect('core:system_settings')

    settings_keys = [
        'site_name', 'site_address', 'site_phone', 'site_email', 'site_currency',
        'email_host', 'email_port', 'email_host_user', 'email_host_password', 'email_use_tls',
        'sms_api_key', 'sms_sender_id',
        'mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 'mpesa_shortcode', 'mpesa_environment',
        'tigo_api_key', 'airtel_api_key',
        'loan_interest_rate', 'loan_max_amount', 'loan_max_duration_months', 'savings_interest_rate',
    ]
    settings = {}
    for key in settings_keys:
        obj = SystemSetting.objects.filter(key=key).first()
        settings[key] = obj.value if obj else ''

    return render(request, 'core/system_settings.html', {'settings': settings, 'page_title': 'System Settings'})


@require_GET
def health_check(request):
    """Public health endpoint — works even when most of the app is degraded."""
    mode = getattr(settings, 'ACTIVE_DB_MODE', 'unknown')
    status = read_db_status(settings.BASE_DIR)
    db_ok = False
    try:
        test_django_connection('default')
        db_ok = True
    except Exception as exc:
        status['connection_error'] = str(exc)[:200]

    primary_ok = status.get('primary_ok', False)
    http_status = 200 if db_ok else 503
    return JsonResponse({
        'status': 'ok' if db_ok else 'degraded',
        'database_connected': db_ok,
        'active_mode': mode,
        'primary_ok': primary_ok,
        'fallback_ok': status.get('fallback_ok', False),
        'message': status.get('message', ''),
        'last_backup': status.get('last_backup'),
        'last_sync_fixture': status.get('last_sync_fixture'),
    }, status=http_status)


@require_GET
def database_status_api(request):
    return health_check(request)


@login_required
@staff_member_required
def database_status_page(request):
    status = read_db_status(settings.BASE_DIR)
    primary_cfg = settings.DATABASES.get('primary') or getattr(settings, 'MYSQL_PRIMARY_CONFIG', {})
    primary_ping = False
    if primary_cfg.get('ENGINE', '').endswith('mysql'):
        primary_ping = mysql_ping(
            primary_cfg.get('HOST', 'localhost'),
            primary_cfg.get('PORT', '3306'),
            primary_cfg.get('USER', 'root'),
            primary_cfg.get('PASSWORD', ''),
            primary_cfg.get('NAME', ''),
        )
    return render(request, 'core/database_status.html', {
        'db_status': status,
        'active_mode': getattr(settings, 'ACTIVE_DB_MODE', 'unknown'),
        'primary_ping': primary_ping,
        'page_title': 'Database Status',
    })
