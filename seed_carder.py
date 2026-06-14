import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')
sys.path.insert(0, '.')
django.setup()

from apps.authentication.models import User
from apps.cooperative.models import Cooperative
from django.contrib.auth import authenticate

print("=" * 60)
print("CARDER / ID OFFICER SEED DATA GENERATOR")
print("=" * 60)

# Create/update carder users for each cooperative
cooperatives = Cooperative.objects.all()
created_count = 0

for coop in cooperatives:
    uname = f"{coop.code.lower()}_carder"
    phone = f"2557{10000000 + coop.id}"
    pwd = 'carder123'

    user, created = User.objects.get_or_create(
        username=uname,
        defaults={
            'phone': phone,
            'first_name': 'Carder',
            'last_name': f'ID-{coop.code}',
            'role': 'carder',
            'cooperative_id': coop.id,
            'is_verified': True,
            'is_phone_verified': True,
        }
    )
    if created:
        created_count += 1
    user.set_password(pwd)
    user.role = 'carder'
    user.cooperative_id = coop.id
    user.is_verified = True
    user.is_phone_verified = True
    user.save()
    print(f"[OK] Carder '{uname}' for {coop.name} (pass: {pwd})")

print(f"\nTotal carder users created: {created_count}")
print()

# Verify logins
print("=== VERIFICATION ===")
for coop in Cooperative.objects.all():
    uname = f"{coop.code.lower()}_carder"
    u = authenticate(username=uname, password='carder123')
    status = 'OK role=' + u.role if u else 'FAILED'
    print(f"  {uname}: {status}")

print()
print("=" * 60)
print("CARDER SEED COMPLETE!")
print("=" * 60)
print()
print("LOGIN CREDENTIALS:")
print("  Username: {cooperative_code}_carder (e.g. amcos001_carder)")
print("  Password: carder123")
print()
print("  Example: amcos001_carder / carder123")
