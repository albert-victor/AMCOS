# Generated manually — adds parrc role choice (display labels in models.py)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_ensure_must_change_password_column'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('cooperative_admin', 'Cooperative Admin'),
                    ('parrc', 'PA-RC'),
                    ('chairperson', 'Mwenyekiti'),
                    ('secretary', 'Katibu'),
                    ('treasurer', 'Mhazini'),
                    ('accountant', 'Mhasibu'),
                    ('loan_officer', 'Afisa Mikopo'),
                    ('auditor', 'Mkaguzi'),
                    ('board_member', 'Mjumbe wa Bodi'),
                    ('carder', 'Carder / ID Officer'),
                    ('member', 'Mwanachama/Mkulima'),
                ],
                default='member',
                max_length=50,
            ),
        ),
    ]
