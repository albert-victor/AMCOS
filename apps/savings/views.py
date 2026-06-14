from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.members.models import Member
from apps.payments.models import Payment
from apps.payments.services import complete_payment
from apps.core.utils import get_cooperative_id, get_obj_or_404_with_coop, scope_member_queryset
from apps.core.permissions import permission_required, access_list_view
import random


def generate_account_number(cooperative_id):
    prefix = f"SAV{cooperative_id:04d}"
    while True:
        number = f"{prefix}{random.randint(100000, 999999)}"
        if not SavingsAccount.objects.filter(account_number=number).exists():
            return number


@access_list_view('savings.list', 'savings.list_own')
def account_list(request):
    cooperative_id = get_cooperative_id(request)
    accounts = SavingsAccount.objects.all()
    if cooperative_id:
        accounts = accounts.filter(cooperative_id=cooperative_id)
    accounts = scope_member_queryset(accounts, request, 'member_id')
    context = {
        'accounts': accounts,
        'total_balance': accounts.aggregate(total=Sum('balance'))['total'] or 0,
        'total_accounts': accounts.count(),
    }
    return render(request, 'savings/list.html', context)


@permission_required('savings.detail')
def account_detail(request, account_id):
    account = get_obj_or_404_with_coop(SavingsAccount, request, account_id)
    transactions = account.transactions.all()[:50]
    return render(request, 'savings/detail.html', {'account': account, 'transactions': transactions})


@login_required
@permission_required('savings.create')
def account_create(request):
    cooperative_id = get_cooperative_id(request)
    members = Member.objects.all()
    if cooperative_id:
        members = members.filter(cooperative_id=cooperative_id, status='active')

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        account_type = request.POST.get('account_type')

        if SavingsAccount.objects.filter(cooperative_id=cooperative_id, member_id=member_id, account_type=account_type, status='active').exists():
            messages.error(request, 'Member already has an active account of this type')
            return render(request, 'savings/create.html', {'members': members})

        account = SavingsAccount.objects.create(
            cooperative_id=cooperative_id,
            member_id=member_id,
            account_number=generate_account_number(cooperative_id),
            account_type=account_type,
            interest_rate=request.POST.get('interest_rate', 3.00),
        )
        messages.success(request, f'Savings account {account.account_number} created')
        return redirect('savings:detail', account_id=account.id)

    return render(request, 'savings/create.html', {'members': members})


@login_required
@permission_required('savings.deposit')
def transaction_deposit(request, account_id):
    account = get_obj_or_404_with_coop(SavingsAccount, request, account_id)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        if amount <= 0:
            messages.error(request, 'Invalid amount')
            return render(request, 'savings/deposit.html', {'account': account})

        account.deposit(amount, request.POST.get('description', ''))

        payment = Payment.objects.create(
            cooperative_id=account.cooperative_id,
            member_id=account.member_id,
            payment_type='savings_deposit',
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

        messages.success(request, f'Deposit of {amount} completed successfully')
        return redirect('savings:detail', account_id=account.id)

    return render(request, 'savings/deposit.html', {'account': account})


@login_required
@permission_required('savings.withdraw')
def transaction_withdraw(request, account_id):
    account = get_obj_or_404_with_coop(SavingsAccount, request, account_id)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        if amount <= 0:
            messages.error(request, 'Invalid amount')
            return render(request, 'savings/withdraw.html', {'account': account})

        if account.balance < amount:
            messages.error(request, 'Insufficient balance')
            return render(request, 'savings/withdraw.html', {'account': account})

        account.withdraw(amount, request.POST.get('description', ''))
        messages.success(request, f'Withdrawal of {amount} completed')
        return redirect('savings:detail', account_id=account.id)

    return render(request, 'savings/withdraw.html', {'account': account})


@permission_required('savings.detail')
def account_statement(request, account_id):
    account = get_obj_or_404_with_coop(SavingsAccount, request, account_id)
    start_date = request.GET.get('from')
    end_date = request.GET.get('to')

    transactions = account.transactions.all()
    if start_date:
        transactions = transactions.filter(created_at__gte=start_date)
    if end_date:
        transactions = transactions.filter(created_at__lte=end_date)

    return render(request, 'savings/statement.html', {
        'account': account,
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
    })
