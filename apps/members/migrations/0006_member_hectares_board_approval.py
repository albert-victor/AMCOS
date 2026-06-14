# Generated for Mgowelo AMCOS registration workflow

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_cardissuance'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='hectares',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Land contributed as shares (minimum 10 hectares per constitution)',
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='member',
            name='hectares_other_note',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='MemberBoardApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('approver_user_id', models.BigIntegerField(db_index=True)),
                ('notes', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('member', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='board_approvals',
                    to='members.member',
                )),
            ],
            options={
                'db_table': 'member_board_approvals',
                'ordering': ['created_at'],
                'unique_together': {('member', 'approver_user_id')},
            },
        ),
    ]
