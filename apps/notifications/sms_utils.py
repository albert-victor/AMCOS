from django.utils import timezone
from .models import SMSLog
import logging

logger = logging.getLogger(__name__)


def send_sms(phone, message, cooperative_id=None, sender_id='MKUUWA'):
    try:
        SMSLog.objects.create(
            cooperative_id=cooperative_id or 0,
            phone=phone,
            message=message,
            sender_id=sender_id,
            status='sent',
            sent_at=timezone.now(),
        )
        logger.info(f'SMS sent to {phone}: {message[:50]}...')
        return True
    except Exception as e:
        logger.error(f'SMS failed to {phone}: {e}')
        return False


def broadcast_sms(phone_list, message, cooperative_id=None, sender_id='MKUUWA'):
    sent = 0
    for phone in phone_list:
        if phone and send_sms(phone, message, cooperative_id, sender_id):
            sent += 1
    return sent
