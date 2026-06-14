from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('governance', '0002_meeting_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='meeting_link',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='meetingattendance',
            name='attendee_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='meetingattendance',
            name='attendee_role',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
