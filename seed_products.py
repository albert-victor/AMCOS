import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')
django.setup()

from decimal import Decimal
from apps.loans.models import LoanProduct
from apps.cooperative.models import Cooperative

cooperatives = Cooperative.objects.filter(status='active')
if not cooperatives:
    print('No active cooperatives found. Run seed_data.py first.')
    sys.exit(1)

categories_map = {
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

count = 0
for coop in cooperatives:
    for name, min_amt, max_amt, max_dur, method in products_data:
        p, created = LoanProduct.objects.get_or_create(
            cooperative_id=coop.id,
            name=name,
            defaults={
                'category': categories_map[name],
                'min_amount': min_amt,
                'max_amount': max_amt,
                'interest_rate': coop.loan_interest_rate or Decimal('12.00'),
                'interest_method': method,
                'min_duration_months': 1,
                'max_duration_months': max_dur,
                'processing_fee': min_amt * Decimal('0.01'),
                'status': 'active',
            }
        )
        if created:
            count += 1
            print(f'  Created: {name} [{categories_map[name]}] for {coop.name}')

print(f'\nDone! Created {count} new loan products. Total: {LoanProduct.objects.count()}')
