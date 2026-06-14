from django.contrib import admin
from .models import ChartOfAccount, JournalEntry, JournalLine, LedgerEntry, Income, Expense, Budget, TrialBalance


@admin.register(ChartOfAccount)
class ChartOfAccountAdmin(admin.ModelAdmin):
    list_display = ['account_code', 'account_name', 'account_type', 'is_active', 'balance']
    list_filter = ['account_type', 'is_active']
    search_fields = ['account_code', 'account_name']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'entry_date', 'description', 'is_posted', 'created_at']
    list_filter = ['is_posted', 'entry_date']


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ['journal_entry', 'account', 'debit', 'credit']


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['account', 'entry_date', 'debit', 'credit', 'balance']


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'income_date', 'received_from', 'receipt_number']
    list_filter = ['category', 'income_date']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'expense_date', 'paid_to', 'is_approved']
    list_filter = ['category', 'is_approved', 'expense_date']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['fiscal_year', 'category', 'budgeted_amount', 'actual_amount']


@admin.register(TrialBalance)
class TrialBalanceAdmin(admin.ModelAdmin):
    list_display = ['account', 'as_at_date', 'debit_balance', 'credit_balance']
