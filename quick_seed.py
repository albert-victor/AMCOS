import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')
import django
django.setup()
from apps.authentication.models import User
from django.contrib.auth import authenticate

for u in User.objects.filter(role='member'):
    u.set_password('member123')
    u.is_verified = True
    u.is_phone_verified = True
    u.save()

data = [
    ('amcos001_member_0','Juma','Mbwana','255712345001',2),
    ('amcos001_member_1','Asha','Ochieng','255712345002',2),
    ('amcos001_member_2','Mariam','Kamau','255712345003',2),
    ('amcos001_member_3','John','Nkya','255712345004',2),
    ('amcos001_member_4','Grace','Kilonzo','255712345005',2),
]
for uname,first,last,phone,coop_id in data:
    obj, created = User.objects.get_or_create(
        username=uname,
        defaults=dict(phone=phone, first_name=first, last_name=last,
            role='member', cooperative_id=coop_id,
            is_verified=True, is_phone_verified=True)
    )
    obj.set_password('member123')
    obj.save()
    print(('Created' if created else 'Updated') + ': ' + uname)

tests = ['amcos001_member_0', 'sacco001_member_0', 'amcos001_member_1']
for t in tests:
    u = authenticate(username=t, password='member123')
    print(t + ': ' + ('OK role='+u.role if u else 'FAILED'))
