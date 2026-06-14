from django.db import models
from django.utils import timezone


class Meeting(models.Model):
    MEETING_TYPES = [
        ('annual_general', 'Annual General Meeting'),
        ('board', 'Board Meeting'),
        ('committee', 'Committee Meeting'),
        ('special', 'Special Meeting'),
        ('emergency', 'Emergency Meeting'),
    ]

    MEETING_STATUS = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    meeting_type = models.CharField(max_length=50, choices=MEETING_TYPES)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    agenda = models.TextField(blank=True)
    meeting_link = models.URLField(blank=True)
    status = models.CharField(max_length=50, choices=MEETING_STATUS, default='scheduled')
    organized_by = models.BigIntegerField()
    minutes = models.TextField(blank=True)
    minutes_uploaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meetings'
        ordering = ['-date', 'start_time']

    def __str__(self):
        return f"{self.title} - {self.date}"


class MeetingAttendance(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='attendance')
    member_id = models.BigIntegerField()
    member_name = models.CharField(max_length=255)
    attendee_phone = models.CharField(max_length=20, blank=True)
    attendee_role = models.CharField(max_length=50, blank=True)
    attended = models.BooleanField(default=False)
    check_in_time = models.DateTimeField(null=True, blank=True)
    signature = models.FileField(upload_to='signatures/', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'meeting_attendance'
        unique_together = ['meeting', 'member_id']

    def __str__(self):
        return f"{self.member_name} - {self.meeting}"


class Resolution(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='resolutions')
    title = models.CharField(max_length=255)
    description = models.TextField()
    proposed_by = models.BigIntegerField()
    seconded_by = models.BigIntegerField(null=True, blank=True)
    votes_for = models.IntegerField(default=0)
    votes_against = models.IntegerField(default=0)
    votes_abstain = models.IntegerField(default=0)
    is_passed = models.BooleanField(default=False)
    implemented = models.BooleanField(default=False)
    implementation_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'resolutions'

    def __str__(self):
        return self.title


class Election(models.Model):
    ELECTION_STATUS = [
        ('pending', 'Pending'),
        ('nomination', 'Nomination Phase'),
        ('campaign', 'Campaign Phase'),
        ('voting', 'Voting Phase'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    nomination_start = models.DateField()
    nomination_end = models.DateField()
    voting_start = models.DateTimeField()
    voting_end = models.DateTimeField()
    status = models.CharField(max_length=50, choices=ELECTION_STATUS, default='pending')
    created_by = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'elections'

    def __str__(self):
        return f"{self.title} - {self.position}"


class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    member_id = models.BigIntegerField()
    member_name = models.CharField(max_length=255)
    manifesto = models.TextField(blank=True)
    photo = models.FileField(upload_to='candidates/', null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    vote_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'candidates'
        unique_together = ['election', 'member_id']

    def __str__(self):
        return f"{self.member_name} - {self.election.position}"


class Vote(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    member_id = models.BigIntegerField()
    voted_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'votes'
        unique_together = ['election', 'member_id']

    def __str__(self):
        return f"{self.member_id} voted for {self.candidate.member_name}"


class MeetingDocument(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='meeting_docs/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'meeting_documents'

    def __str__(self):
        return self.title


class MeetingComment(models.Model):
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    author_user_id = models.BigIntegerField(db_index=True)
    author_role = models.CharField(max_length=50)
    author_name = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'meeting_comments'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author_name} -> {self.meeting_id}'
