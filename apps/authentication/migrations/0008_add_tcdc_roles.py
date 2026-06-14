# Tume ya Maendeleo ya Ushirika (TCDC) — wilaya + mkoa read-only oversight roles

from django.db import migrations, models


ROLE_CHOICES = [
    ('super_admin', 'Super Admin'),
    ('cooperative_admin', 'Cooperative Admin'),
    ('parrc', 'PA-RC'),
    ('chairperson', 'Mwenyekiti'),
    ('vice_chairperson', 'Makamu wa Mwenyekiti'),
    ('secretary', 'Katibu'),
    ('vice_secretary', 'Makamu Katibu'),
    ('treasurer', 'Mhazini'),
    ('accountant', 'Mhasibu'),
    ('loan_officer', 'Afisa Mikopo'),
    ('auditor', 'Mkaguzi'),
    ('board_member', 'Mjumbe wa Bodi'),
    ('carder', 'Carder / ID Officer'),
    ('tcdc_wilaya', 'TCDC — Ngazi ya Wilaya'),
    ('tcdc_mkoa', 'TCDC — Ngazi ya Mkoa'),
    ('member', 'Mwanachama/Mkulima'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0007_leadership_roles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=ROLE_CHOICES,
                default='member',
                max_length=50,
            ),
        ),
    ]
