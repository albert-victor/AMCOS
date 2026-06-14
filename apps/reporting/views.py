from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import HttpResponse
import csv

from apps.core.utils import get_cooperative_id
from apps.core.permissions import permission_required

from .models import ReportTemplate, GeneratedReport
from apps.members.models import Member
from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.loans.models import Loan, LoanRepayment
from apps.payments.models import Payment


@permission_required('reporting.view')
def report_dashboard(request):
    cooperative_id = get_cooperative_id(request)
    reports = GeneratedReport.objects.all()
    if cooperative_id:
        reports = reports.filter(cooperative_id=cooperative_id)
    reports = reports[:20]
    return render(request, 'reporting/dashboard.html', {'reports': reports})


@permission_required('reporting.view')
def member_report(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.all()
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id)

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="members_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Member Number', 'Name', 'Phone', 'Email', 'Status', 'Joined Date'])
        for m in members:
            writer.writerow([m.member_number, m.full_name, m.phone, m.email, m.status, m.joined_at])
        return response

    return render(request, 'reporting/member_report.html', {
        'members': members,
        'total': members.count(),
        'active': members.filter(status='active').count(),
    })


@permission_required('reporting.view')
def savings_report(request):
    cooperative_id = get_cooperative_id(request)
    accounts = SavingsAccount.objects.all()
    if cooperative_id:
        accounts = accounts.filter(cooperative_id=cooperative_id)
    total_balance = accounts.aggregate(total=Sum('balance'))['total'] or 0

    return render(request, 'reporting/savings_report.html', {
        'accounts': accounts,
        'total_balance': total_balance,
        'total_accounts': accounts.count(),
    })


@permission_required('reporting.view')
def loan_report(request):
    cooperative_id = get_cooperative_id(request)
    loans = Loan.objects.all()
    if cooperative_id:
        loans = loans.filter(cooperative_id=cooperative_id)
    total_disbursed = loans.filter(status__in=['disbursed', 'active', 'completed']).aggregate(total=Sum('amount'))['total'] or 0
    total_outstanding = loans.filter(status__in=['active', 'defaulted']).aggregate(total=Sum('balance'))['total'] or 0

    return render(request, 'reporting/loan_report.html', {
        'loans': loans,
        'total_disbursed': total_disbursed,
        'total_outstanding': total_outstanding,
        'defaulted': loans.filter(status='defaulted').count(),
    })


@permission_required('reporting.view')
def payment_report(request):
    cooperative_id = get_cooperative_id(request)
    payments = Payment.objects.all()
    if cooperative_id:
        payments = payments.filter(cooperative_id=cooperative_id)
    total_collected = payments.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'reporting/payment_report.html', {
        'payments': payments[:100],
        'total_collected': total_collected,
        'total_transactions': payments.count(),
    })
