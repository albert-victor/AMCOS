from django.db import models
from django.utils import timezone
from django.conf import settings


class Conversation(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=255, blank=True)
    is_group = models.BooleanField(default=False)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'Conversation {self.id}'


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user_id = models.BigIntegerField(db_index=True)
    joined_at = models.DateTimeField(default=timezone.now)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conversation_participants'
        unique_together = [('conversation', 'user_id')]

    def __str__(self):
        return f'User {self.user_id} in Conversation {self.conversation_id}'


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.BigIntegerField(db_index=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f'Message from {self.sender_id} at {self.created_at}'


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('system', 'System'),
        ('payment', 'Payment'),
        ('savings', 'Savings'),
        ('loan', 'Loan'),
        ('meeting', 'Meeting'),
        ('election', 'Election'),
        ('approval', 'Approval'),
        ('reminder', 'Reminder'),
        ('alert', 'Alert'),
        ('promotion', 'Promotion'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    user_id = models.BigIntegerField(db_index=True)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='normal')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_via_email = models.BooleanField(default=False)
    sent_via_sms = models.BooleanField(default=False)
    sent_via_push = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'is_read']),
            models.Index(fields=['cooperative_id', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user_id}"


class SMSLog(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    phone = models.CharField(max_length=20)
    message = models.TextField()
    sender_id = models.CharField(max_length=50, default='MKUUWA')
    status = models.CharField(max_length=50, default='pending',
                              choices=[
                                  ('pending', 'Pending'),
                                  ('sent', 'Sent'),
                                  ('delivered', 'Delivered'),
                                  ('failed', 'Failed'),
                              ])
    provider = models.CharField(max_length=50, default='custom')
    reference = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'sms_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS to {self.phone} - {self.status}"


class EmailLog(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=50, default='pending',
                              choices=[
                                  ('pending', 'Pending'),
                                  ('sent', 'Sent'),
                                  ('opened', 'Opened'),
                                  ('failed', 'Failed'),
                              ])
    opened_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Email to {self.recipient} - {self.subject}"
