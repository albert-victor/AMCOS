# Generated manually
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('governance', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeetingComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_user_id', models.BigIntegerField(db_index=True)),
                ('author_role', models.CharField(max_length=50)),
                ('author_name', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                (
                    'meeting',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='governance.meeting'),
                ),
            ],
            options={
                'db_table': 'meeting_comments',
                'ordering': ['-created_at'],
            },
        ),
    ]

