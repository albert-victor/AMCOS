from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0006_add_parrc_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='leadership_role',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'None'),
                    ('board_member', 'Mjumbe wa Bodi'),
                    ('vice_chairperson', 'Makamu wa Mwenyekiti'),
                    ('vice_secretary', 'Makamu Katibu'),
                ],
                default='',
                help_text='Optional leadership title while account remains a member.',
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
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
                    ('member', 'Mwanachama/Mkulima'),
                ],
                default='member',
                max_length=50,
            ),
        ),
    ]
