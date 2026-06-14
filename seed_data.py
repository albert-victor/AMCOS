import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')
django.setup()

from apps.authentication.models import User
from apps.cooperative.models import Cooperative, Branch
from apps.members.models import Member, MemberCategory, NextOfKin
from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.loans.models import LoanProduct, Loan, LoanRepayment
from apps.shares.models import Share, ShareTransaction
from apps.payments.models import Payment
from apps.accounting.models import ChartOfAccount, Income, Expense
from apps.governance.models import Meeting
from django.utils import timezone

print("=" * 60)
print("MKUU WA MKOA - SEED DATA GENERATOR")
print("=" * 60)

# 1. Ensure superuser exists
admin, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'phone': '255712345678',
        'email': 'admin@mkukuwa.com',
        'role': 'super_admin',
        'is_superuser': True,
        'is_staff': True,
        'is_active': True,
        'first_name': 'System',
        'last_name': 'Admin',
    }
)
if created:
    admin.set_password('admin123')
    admin.save()
    print(f"[OK] Superuser 'admin' created (pass: admin123)")
else:
    admin.set_password('admin123')
    admin.save()
    print(f"[OK] Superuser 'admin' password reset to admin123")

# 2. Create Cooperatives with sample data
cooperatives_data = [
    {'name': 'SACCO Mkuu wa Mkoa', 'code': 'SACCO001', 'type': 'sacco', 'plan': 'enterprise'},
    {'name': 'Wakulima AMCOS', 'code': 'AMCOS001', 'type': 'amcos', 'plan': 'professional'},
    {'name': 'Vikoba Jumuishi', 'code': 'VIKOBA01', 'type': 'vikoba', 'plan': 'basic'},
    {'name': 'Teachers SACCO', 'code': 'TEACH01', 'type': 'sacco', 'plan': 'professional'},
    {'name': 'Farmers Cooperative', 'code': 'FARM001', 'type': 'farmers', 'plan': 'basic'},
]

cooperatives = []
for cd in cooperatives_data:
    coop, created = Cooperative.objects.get_or_create(
        code=cd['code'],
        defaults={
            'name': cd['name'],
            'type': cd['type'],
            'subscription_plan': cd['plan'],
            'status': 'active',
            'phone': f'2557{random.randint(10000000, 99999999)}',
            'email': f'info@{cd["code"].lower()}.co.tz',
            'registration_fee': 100000,
            'membership_fee': 5000,
            'share_price': 5000,
            'interest_rate': Decimal(str(random.choice([3.0, 3.5, 4.0, 5.0]))),
            'loan_interest_rate': Decimal(str(random.choice([10, 12, 15, 18]))),
            'city': random.choice(['Dar es Salaam', 'Arusha', 'Mwanza', 'Mbeya', 'Dodoma']),
            'region': random.choice(['Dar', 'Arusha', 'Mwanza', 'Mbeya', 'Dodoma']),
        }
    )
    cooperatives.append(coop)
    print(f"[OK] Cooperative: {coop.name} ({coop.code})")

# 3. Create role-based management users for each cooperative
management_roles = [
    ('parrc', 'PA-RC', 'ALLY', 'A. NGWEJA', 'amcos123'),
    ('chairperson', 'Mwenyekiti', 'James', 'Mkumbo', 'chair123'),
    ('secretary', 'Katibu', 'Anna', 'Katibu', 'sec123'),
    ('treasurer', 'Mhazini', 'Peter', 'Mhazini', 'treas123'),
    ('accountant', 'Mhasibu', 'Michael', 'Mhasibu', 'acc123'),
    ('board_member', 'MjumbeBodi', 'Sarah', 'Bodi', 'board123'),
    ('carder', 'Carder', 'Idd', 'Carder', 'carder123'),
]

for coop in cooperatives:
    for role_key, role_label, first, last, pwd in management_roles:
        uname = f"{coop.code.lower()}_{role_key}"
        if not User.objects.filter(username=uname).exists():
            user = User.objects.create_user(
                username=uname,
                phone=f"2557{random.randint(10000000, 99999999)}",
                password=pwd,
                first_name=first,
                last_name=last,
                role=role_key,
                cooperative_id=coop.id,
                is_verified=True,
                is_phone_verified=True,
            )
            print(f"[OK] {role_label} user '{uname}' created (pass: {pwd})")
        else:
            user = User.objects.get(username=uname)
            if role_key == 'parrc' and (
                user.first_name != first or user.last_name != last
            ):
                user.first_name = first
                user.last_name = last
                user.save(update_fields=['first_name', 'last_name'])
                print(f"[OK] {role_label} user '{uname}' name updated to {first} {last}")
            elif role_key == 'chairperson' and user.first_name == 'ALLY' and user.last_name == 'A. NGWEJA':
                user.first_name = first
                user.last_name = last
                user.save(update_fields=['first_name', 'last_name'])
                print(f"[OK] Chairperson '{uname}' restored to {first} {last}")
            else:
                print(f"[OK] {role_label} user '{uname}' already exists")

# 4. Link admin to first cooperative
admin.cooperative_id = cooperatives[0].id
admin.save()

# 5. Create Branches
branch_names = ['Main Branch', 'Downtown Branch', 'Kariakoo Branch', 'Mlimani City', 'Kigamboni']
for coop in cooperatives[:3]:
    for bn in branch_names[:3]:
        Branch.objects.get_or_create(
            cooperative=coop,
            code=f"{coop.code}-{bn[:3].upper()}",
            defaults={'name': f"{bn} - {coop.name}", 'city': coop.city, 'status': 'active'}
        )
print(f"[OK] Branches created for {len(cooperatives[:3])} cooperatives")

# 6. Create Member Categories for each cooperative
for coop in cooperatives:
    for cat_name, min_sav, multiplier in [
        ('Regular Member', 5000, 3),
        ('Premium Member', 50000, 5),
        ('Corporate Member', 200000, 10),
    ]:
        MemberCategory.objects.get_or_create(
            cooperative_id=coop.id,
            name=cat_name,
            defaults={
                'description': f'{cat_name} category',
                'min_savings': min_sav,
                'max_loan_multiplier': multiplier,
            }
        )
print(f"[OK] Member categories created")

# 7. Create Chart of Accounts for each cooperative
accounts_template = [
    ('1001', 'Cash', 'asset'),
    ('1002', 'Bank Account', 'asset'),
    ('1003', 'Loan Receivables', 'asset'),
    ('1004', 'Accounts Receivable', 'asset'),
    ('1005', 'Fixed Assets', 'asset'),
    ('2001', 'Member Savings', 'liability'),
    ('2002', 'Member Deposits', 'liability'),
    ('2003', 'Loans Payable', 'liability'),
    ('3001', 'Share Capital', 'equity'),
    ('3002', 'Retained Earnings', 'equity'),
    ('4001', 'Membership Fees', 'income'),
    ('4002', 'Loan Interest', 'income'),
    ('4003', 'Investment Income', 'income'),
    ('5001', 'Salaries', 'expense'),
    ('5002', 'Rent', 'expense'),
    ('5003', 'Utilities', 'expense'),
    ('5004', 'Administrative', 'expense'),
]

for coop in cooperatives:
    for code, name, atype in accounts_template:
        ChartOfAccount.objects.get_or_create(
            cooperative_id=coop.id,
            account_code=code,
            defaults={
                'account_name': f"{name} - {coop.code}",
                'account_type': atype,
                'description': f'{name} account for {coop.name}',
            }
        )
print(f"[OK] Chart of Accounts created for {len(cooperatives)} cooperatives")

# 8. Create Members and Users for each cooperative
member_first_names = ['Juma', 'Asha', 'Mariam', 'John', 'Grace', 'Peter', 'Anna', 'David', 'Sarah', 'Michael',
                      'Fatima', 'Joseph', 'Elizabeth', 'Emmanuel', 'Rose', 'Daniel', 'Amina', 'Samuel', 'Neema', 'James']
member_last_names = ['Mwangi', 'Ochieng', 'Kamau', 'Nkya', 'Kilonzo', 'Mbwana', 'Mushi', 'Lema', 'Kipruto', 'Simiyu']

members = []
for coop in cooperatives:
    for i in range(random.randint(5, 15)):
        first = random.choice(member_first_names)
        last = random.choice(member_last_names)
        phone = f"2557{random.randint(10000000, 99999999)}"
        uname = f"{coop.code.lower()}_member_{i}"

        if User.objects.filter(username=uname).exists():
            continue

        user = User.objects.create_user(
            username=uname,
            phone=phone,
            password='member123',
            first_name=first,
            last_name=last,
            role='member',
            cooperative_id=coop.id,
            is_verified=True,
            is_phone_verified=True,
        )

        member_num = f"MEM{coop.id:04d}{i+1:04d}"
        member = Member.objects.create(
            cooperative_id=coop.id,
            user_id=user.id,
            member_number=member_num,
            first_name=first,
            last_name=last,
            phone=phone,
            gender=random.choice(['male', 'female']),
            status='active',
            is_approved=True,
            approved_by=admin.id,
            approved_at=timezone.now(),
        )

        NextOfKin.objects.create(
            member=member,
            full_name=f"{random.choice(member_first_names)} {random.choice(member_last_names)}",
            relationship=random.choice(['spouse', 'child', 'parent', 'sibling']),
            phone=f"2557{random.randint(10000000, 99999999)}",
            is_primary=True,
        )

        members.append(member)
        print(f"  [+] Member: {member.member_number} - {member.full_name} ({coop.code})")

print(f"[OK] Total members created: {len(members)}")

# 9. Create Savings Accounts with transactions
savings_accounts = []
for member in members[:50]:
    acct_num = f"SAV{member.cooperative_id:04d}{member.id:04d}"
    if SavingsAccount.objects.filter(account_number=acct_num).exists():
        continue

    account = SavingsAccount.objects.create(
        cooperative_id=member.cooperative_id,
        member_id=member.id,
        account_number=acct_num,
        account_type=random.choice(['voluntary', 'mandatory', 'fixed_deposit']),
        balance=Decimal(str(random.randint(50000, 5000000))),
        interest_rate=Decimal('3.50'),
        status='active',
    )
    savings_accounts.append(account)

    for d in range(random.randint(3, 10)):
        amt = Decimal(str(random.randint(10000, 500000)))
        SavingsTransaction.objects.create(
            cooperative_id=account.cooperative_id,
            member_id=account.member_id,
            account=account,
            transaction_type='deposit',
            amount=amt,
            balance_before=account.balance - amt,
            balance_after=account.balance,
            description=f'Salary deposit {d+1}',
            created_at=timezone.now() - timedelta(days=d * 15),
        )

print(f"[OK] Savings accounts created: {len(savings_accounts)}")

# 10. Create Loan Products
product_categories_map = {
    'Personal Loan': 'general',
    'Business Loan': 'general',
    'Emergency Loan': 'general',
    'Education Loan': 'general',
    'Agriculture Loan': 'agricultural_crops',
    'Tractor Loan': 'tractors',
    'Farming Equipment Loan': 'farming_equipment',
    'Crop Production Loan': 'agricultural_crops',
}
products_data = [
    ('Personal Loan', 50000, 5000000, 12, 'flat'),
    ('Business Loan', 200000, 20000000, 24, 'reducing'),
    ('Emergency Loan', 10000, 500000, 3, 'flat'),
    ('Education Loan', 100000, 10000000, 36, 'reducing'),
    ('Agriculture Loan', 50000, 15000000, 18, 'reducing'),
    ('Tractor Loan', 500000, 50000000, 36, 'reducing'),
    ('Farming Equipment Loan', 200000, 20000000, 24, 'reducing'),
    ('Crop Production Loan', 100000, 10000000, 12, 'flat'),
]
for coop in cooperatives:
    for name, min_amt, max_amt, max_dur, method in products_data:
        LoanProduct.objects.get_or_create(
            cooperative_id=coop.id,
            name=name,
            defaults={
                'min_amount': min_amt,
                'max_amount': max_amt,
                'interest_rate': coop.loan_interest_rate,
                'interest_method': method,
                'min_duration_months': 1,
                'max_duration_months': max_dur,
                'processing_fee': min_amt * Decimal('0.01'),
                'category': product_categories_map.get(name, 'general'),
            }
        )
print(f"[OK] Loan products created")

# 11. Create Loans
loans_created = 0
for member in members[:30]:
    products = LoanProduct.objects.filter(cooperative_id=member.cooperative_id)
    if not products.exists():
        continue
    product = random.choice(list(products))
    amt = Decimal(str(random.randint(int(product.min_amount), min(int(product.max_amount), 2000000))))
    duration = random.randint(3, 12)

    loan_num = f"LN{member.cooperative_id:04d}{member.id:04d}"
    if Loan.objects.filter(loan_number=loan_num).exists():
        continue

    loan = Loan.objects.create(
        cooperative_id=member.cooperative_id,
        member_id=member.id,
        product=product,
        loan_number=loan_num,
        amount=amt,
        interest_rate=product.interest_rate,
        interest_method=product.interest_method,
        duration_months=duration,
        processing_fee=product.processing_fee,
        purpose=random.choice(['Business expansion', 'School fees', 'Home improvement', 'Emergency', 'Agriculture']),
        status=random.choice(['active', 'completed', 'active', 'disbursed']),
        disbursed_at=timezone.now() - timedelta(days=random.randint(30, 200)),
    )
    loan.calculate_installment()
    loan.save()
    loans_created += 1

    if loan.status in ['active', 'completed']:
        paid_months = duration if loan.status == 'completed' else random.randint(1, max(1, duration - 1))
        for m in range(paid_months):
            repay_amt = loan.monthly_installment
            LoanRepayment.objects.create(
                loan=loan,
                cooperative_id=loan.cooperative_id,
                member_id=loan.member_id,
                amount=repay_amt,
                principal_paid=repay_amt * Decimal('0.7'),
                interest_paid=repay_amt * Decimal('0.3'),
                balance_before=loan.balance,
                balance_after=loan.balance - repay_amt,
                payment_method=random.choice(['cash', 'mpesa', 'bank_transfer']),
                due_date=timezone.now().date() - timedelta(days=(duration - m) * 30),
                created_at=timezone.now() - timedelta(days=(duration - m) * 30),
            )
            loan.amount_paid += repay_amt
            loan.balance -= repay_amt
        if loan.status == 'completed':
            loan.completion_date = timezone.now().date()
        loan.save()

print(f"[OK] Loans created: {loans_created}")

# 12. Create Share Holdings
for member in members[:40]:
    share, _ = Share.objects.get_or_create(
        cooperative_id=member.cooperative_id,
        member_id=member.id,
        defaults={
            'certificate_number': f"SH{member.cooperative_id:04d}{member.id:04d}",
            'total_shares': random.randint(5, 100),
            'total_value': Decimal(str(random.randint(50000, 1000000))),
            'status': 'active',
        }
    )
    for t in range(random.randint(1, 3)):
        qty = random.randint(1, 20)
        price = Decimal(str(random.randint(1000, 10000)))
        ShareTransaction.objects.create(
            cooperative_id=share.cooperative_id,
            member_id=share.member_id,
            share=share,
            transaction_type='purchase',
            quantity=qty,
            price_per_share=price,
            total_amount=qty * price,
            created_at=timezone.now() - timedelta(days=random.randint(30, 365)),
        )

print(f"[OK] Share holdings created")

# 13. Create Payments
payment_types = ['registration_fee', 'membership_fee', 'share_purchase', 'savings_deposit', 'loan_repayment']
payment_methods = ['cash', 'mpesa', 'bank_transfer', 'tigo_pesa', 'airtel_money']
for member in members:
    for _ in range(random.randint(1, 5)):
        amt = Decimal(str(random.randint(5000, 200000)))
        ptype = random.choice(payment_types)
        Payment.objects.create(
            cooperative_id=member.cooperative_id,
            member_id=member.id,
            payment_type=ptype,
            payment_method=random.choice(payment_methods),
            amount=amt,
            reference_number=f"PAY{member.cooperative_id:04d}{random.randint(10000, 99999)}",
            status=random.choice(['completed', 'completed', 'completed', 'pending']),
            receipt_number=f"RCP{random.randint(100000, 999999)}",
            payment_date=timezone.now() - timedelta(days=random.randint(1, 180)),
            confirmed_by=admin.id,
            confirmed_at=timezone.now(),
        )

print(f"[OK] Payments created")

# 14. Create Income & Expenses
for coop in cooperatives:
    for d in range(30):
        inc_date = timezone.now().date() - timedelta(days=d)
        Income.objects.create(
            cooperative_id=coop.id,
            category=random.choice(['Membership Fees', 'Loan Interest', 'Investment Income', 'Registration Fees']),
            amount=Decimal(str(random.randint(100000, 2000000))),
            description=f'Daily income {inc_date}',
            income_date=inc_date,
            created_by=admin.id,
        )
        Expense.objects.create(
            cooperative_id=coop.id,
            category=random.choice(['Salaries', 'Rent', 'Utilities', 'Office Supplies', 'Transport']),
            amount=Decimal(str(random.randint(50000, 500000))),
            description=f'Daily expense {inc_date}',
            expense_date=inc_date,
            created_by=admin.id,
            is_approved=True,
        )
print(f"[OK] Income & Expenses created")

# 15. Create Meetings
for coop in cooperatives:
    for i in range(3):
        m_date = timezone.now().date() - timedelta(days=i * 45)
        Meeting.objects.create(
            cooperative_id=coop.id,
            title=f"{['Annual General', 'Board', 'Committee'][i]} Meeting - {coop.name}",
            meeting_type=['annual_general', 'board', 'committee'][i],
            description=f'Regular {["AGM", "board", "committee"][i]} meeting',
            venue=random.choice(['Cooperative Hall', 'Conference Room', 'Online']),
            date=m_date,
            start_time=timezone.now().time(),
            status=random.choice(['completed', 'completed', 'scheduled']),
            organized_by=admin.id,
            minutes=f'Minutes of the meeting held on {m_date}...',
        )
print(f"[OK] Meetings created")

print()
print("=" * 60)
print("SEED DATA GENERATION COMPLETE!")
print("=" * 60)
print()
print("LOGIN CREDENTIALS:")
print("  Super Admin:")
print("    Username: admin")
print("    Password: admin123")
print()
print("  Management Users (per cooperative):")
print("    PA-RC       -> username: {code}_parrc / password: chair123")
print("    Mwenyekiti  -> username: {code}_chairperson / password: chair123")
print("    Katibu      -> username: {code}_secretary   / password: sec123")
print("    Mhazini     -> username: {code}_treasurer   / password: treas123")
print("    Mhasibu     -> username: {code}_accountant  / password: acc123")
print("    MjumbeBodi  -> username: {code}_board_member / password: board123")
print("    Carder      -> username: {code}_carder      / password: carder123")
print()
print("  Sample Members (any cooperative):")
print("    Username: sacco001_member_0 (through sacco001_member_14)")
print("    Password: member123")
print()
print(f"  Cooperatives: {[c.code for c in cooperatives]}")
print(f"  Example PA-RC: amcos001_parrc / amcos123 | Mwenyekiti: amcos001_chairperson / chair123")
print()
