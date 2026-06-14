"""Single-cooperative defaults for MGOWELO AMCOS."""
from django.conf import settings

from apps.cooperative.models import Cooperative


def get_mgowelo_cooperative():
    code = getattr(settings, 'MGOWELO_COOPERATIVE_CODE', 'AMCOS001')
    coop, created = Cooperative.objects.get_or_create(
        code=code,
        defaults={
            'name': 'MGOWELO MULTI-FARMERS ASSOCIATION LTD',
            'type': 'amcos',
            'subscription_plan': 'professional',
            'status': 'active',
            'phone': '255754000001',
            'email': 'info@mgoweloamcos.co.tz',
            'registration_fee': 100000,
            'membership_fee': 5000,
            'share_price': 100000,
            'city': 'Kilolo',
            'region': 'Iringa',
        },
    )
    if created or coop.name != 'MGOWELO MULTI-FARMERS ASSOCIATION LTD':
        coop.name = 'MGOWELO MULTI-FARMERS ASSOCIATION LTD'
        coop.registration_fee = coop.registration_fee or 100000
        coop.share_price = coop.share_price or 100000
        coop.status = 'active'
        coop.save()
    return coop
