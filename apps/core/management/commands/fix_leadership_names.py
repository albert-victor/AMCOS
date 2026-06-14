"""Restore PA-RC vs Mwenyekiti names — Ally Ngweja is PA-RC only."""
from django.core.management.base import BaseCommand

from apps.authentication.models import User

PARRC_FIRST = 'ALLY'
PARRC_LAST = 'A. NGWEJA'
CHAIR_FIRST = 'James'
CHAIR_LAST = 'Mkumbo'


class Command(BaseCommand):
    help = 'Ensure Ally Ngweja is only on parrc; restore chairperson names to James Mkumbo.'

    def handle(self, *args, **options):
        parrc_updated = User.objects.filter(role='parrc').update(
            first_name=PARRC_FIRST, last_name=PARRC_LAST
        )
        chair_fixed = User.objects.filter(
            role='chairperson', first_name=PARRC_FIRST, last_name=PARRC_LAST
        ).update(first_name=CHAIR_FIRST, last_name=CHAIR_LAST)

        self.stdout.write(self.style.SUCCESS(
            f'PA-RC accounts set to {PARRC_FIRST} {PARRC_LAST}: {parrc_updated}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Chairperson accounts restored to {CHAIR_FIRST} {CHAIR_LAST}: {chair_fixed}'
        ))
        for role in ('parrc', 'chairperson', 'secretary'):
            self.stdout.write(f'--- {role} ---')
            for u in User.objects.filter(role=role).order_by('username')[:20]:
                self.stdout.write(f'  {u.username} | {u.get_full_name()}')
