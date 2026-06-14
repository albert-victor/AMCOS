# Generated manually
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('loans', '0002_add_product_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoanBoardDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('board_member_user_id', models.BigIntegerField(db_index=True)),
                ('decision', models.CharField(choices=[('approve', 'Approve'), ('reject', 'Reject')], max_length=10)),
                ('reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                (
                    'loan',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='board_decisions', to='loans.loan'),
                ),
            ],
            options={
                'db_table': 'loan_board_decisions',
                'ordering': ['-created_at'],
                'unique_together': {('loan', 'board_member_user_id')},
            },
        ),
    ]

