from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.core.utils import get_cooperative_id
from apps.core.permissions import permission_required

from .models import ChartOfAccount, JournalEntry, JournalLine, LedgerEntry, Income, Expense, Budget, TrialBalance


@permission_required('accounting.view')
def dashboard(request):
    cooperative_id = get_cooperative_id(request)
    incomes = Income.objects.all()
    expenses = Expense.objects.all()
    if cooperative_id:
        incomes = incomes.filter(cooperative_id=cooperative_id)
        expenses = expenses.filter(cooperative_id=cooperative_id)
    income_total = incomes.aggregate(total=Sum('amount'))['total'] or 0
    expense_total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    recent_income = incomes[:10]
    recent_expenses = expenses[:10]

    return render(request, 'accounting/dashboard.html', {
        'income_total': income_total,
        'expense_total': expense_total,
        'net_income': income_total - expense_total,
        'recent_income': recent_income,
        'recent_expenses': recent_expenses,
    })


@permission_required('accounting.view')
def chart_of_accounts(request):
    cooperative_id = get_cooperative_id(request)
    accounts = ChartOfAccount.objects.all()
    if cooperative_id:
        accounts = accounts.filter(cooperative_id=cooperative_id)
    return render(request, 'accounting/chart_of_accounts.html', {'accounts': accounts})


@permission_required('accounting.create')
def account_create(request):
    if request.method == 'POST':
        cooperative_id = get_cooperative_id(request)
        ChartOfAccount.objects.create(
            cooperative_id=cooperative_id,
            account_code=request.POST.get('account_code'),
            account_name=request.POST.get('account_name'),
            account_type=request.POST.get('account_type'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Account created successfully')
        return redirect('accounting:chart_of_accounts')
    return render(request, 'accounting/account_form.html')


@permission_required('accounting.view')
def income_list(request):
    cooperative_id = get_cooperative_id(request)
    incomes = Income.objects.all()
    if cooperative_id:
        incomes = incomes.filter(cooperative_id=cooperative_id)
    total = incomes.aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'accounting/income_list.html', {'incomes': incomes, 'total': total})


@permission_required('accounting.create')
def income_create(request):
    if request.method == 'POST':
        cooperative_id = get_cooperative_id(request)
        Income.objects.create(
            cooperative_id=cooperative_id,
            category=request.POST.get('category'),
            amount=request.POST.get('amount'),
            description=request.POST.get('description', ''),
            income_date=request.POST.get('income_date'),
            received_from=request.POST.get('received_from', ''),
            payment_method=request.POST.get('payment_method', ''),
            created_by=request.user.id,
        )
        messages.success(request, 'Income recorded successfully')
        return redirect('accounting:income_list')
    return render(request, 'accounting/income_form.html')


@permission_required('accounting.view')
def expense_list(request):
    cooperative_id = get_cooperative_id(request)
    expenses = Expense.objects.all()
    if cooperative_id:
        expenses = expenses.filter(cooperative_id=cooperative_id)
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'accounting/expense_list.html', {'expenses': expenses, 'total': total})


@permission_required('accounting.create')
def expense_create(request):
    if request.method == 'POST':
        cooperative_id = get_cooperative_id(request)
        Expense.objects.create(
            cooperative_id=cooperative_id,
            category=request.POST.get('category'),
            amount=request.POST.get('amount'),
            description=request.POST.get('description', ''),
            expense_date=request.POST.get('expense_date'),
            paid_to=request.POST.get('paid_to', ''),
            payment_method=request.POST.get('payment_method', ''),
            created_by=request.user.id,
        )
        messages.success(request, 'Expense recorded successfully')
        return redirect('accounting:expense_list')
    return render(request, 'accounting/expense_form.html')


@permission_required('accounting.view')
def budget_list(request):
    cooperative_id = get_cooperative_id(request)
    budgets = Budget.objects.all()
    if cooperative_id:
        budgets = budgets.filter(cooperative_id=cooperative_id)
    return render(request, 'accounting/budget_list.html', {'budgets': budgets})


@permission_required('accounting.create')
def budget_create(request):
    if request.method == 'POST':
        cooperative_id = get_cooperative_id(request)
        Budget.objects.create(
            cooperative_id=cooperative_id,
            fiscal_year=request.POST.get('fiscal_year'),
            category=request.POST.get('category'),
            budgeted_amount=request.POST.get('budgeted_amount'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Budget created successfully')
        return redirect('accounting:budget_list')
    return render(request, 'accounting/budget_form.html')


@permission_required('accounting.view')
def trial_balance(request):
    cooperative_id = get_cooperative_id(request)
    accounts = ChartOfAccount.objects.filter(is_active=True).order_by('account_code')
    if cooperative_id:
        accounts = accounts.filter(cooperative_id=cooperative_id)
    total_debit = accounts.filter(account_type__in=['asset', 'expense']).aggregate(total=Sum('balance'))['total'] or 0
    total_credit = accounts.filter(account_type__in=['liability', 'equity', 'income']).aggregate(total=Sum('balance'))['total'] or 0

    return render(request, 'accounting/trial_balance.html', {
        'accounts': accounts,
        'total_debit': total_debit,
        'total_credit': total_credit,
    })


@permission_required('accounting.view')
def income_statement(request):
    cooperative_id = get_cooperative_id(request)
    incomes = Income.objects.all()
    expenses = Expense.objects.all()
    if cooperative_id:
        incomes = incomes.filter(cooperative_id=cooperative_id)
        expenses = expenses.filter(cooperative_id=cooperative_id)
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0
    net = total_income - total_expense

    return render(request, 'accounting/income_statement.html', {
        'incomes': incomes,
        'expenses': expenses,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': net,
    })


@permission_required('accounting.view')
def balance_sheet(request):
    cooperative_id = get_cooperative_id(request)
    accounts_qs = ChartOfAccount.objects.all()
    if cooperative_id:
        accounts_qs = accounts_qs.filter(cooperative_id=cooperative_id)
    assets = accounts_qs.filter(account_type='asset')
    liabilities = accounts_qs.filter(account_type='liability')
    equity = accounts_qs.filter(account_type='equity')

    total_assets = assets.aggregate(total=Sum('balance'))['total'] or 0
    total_liabilities = liabilities.aggregate(total=Sum('balance'))['total'] or 0
    total_equity = equity.aggregate(total=Sum('balance'))['total'] or 0

    return render(request, 'accounting/balance_sheet.html', {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
    })
