from django.shortcuts import render, redirect, get_object_or_404
from apps.core.permissions import permission_required
from django.contrib import messages as django_messages
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse

from .models import Notification, Conversation, ConversationParticipant, Message
from .sms_utils import broadcast_sms
from apps.members.models import Member
from apps.authentication.models import User
from apps.core.utils import get_cooperative_id


def get_cooperative_users(cooperative_id, role_filter=None):
    qs = User.objects.all()
    if cooperative_id:
        qs = qs.filter(cooperative_id=cooperative_id)
    if role_filter == 'members':
        qs = qs.filter(role='member')
    elif role_filter == 'staff':
        qs = qs.exclude(role='member')
    return qs


# ─── Notifications ──────────────────────────────────────────────────

@permission_required('notifications.inbox')
def notification_list(request):
    notifications = Notification.objects.filter(user_id=request.user.id)
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'notifications/list.html', {
        'notifications': notifications[:50],
        'unread_count': unread_count,
    })


@permission_required('notifications.inbox')
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user_id=request.user.id)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    return redirect(notification.link if notification.link else 'notifications:list')


@permission_required('notifications.inbox')
def notification_mark_all_read(request):
    Notification.objects.filter(user_id=request.user.id, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    django_messages.success(request, 'Taarifa zote zimesomwa')
    return redirect('notifications:list')


@permission_required('notifications.broadcast')
def broadcast(request):
    """Mass announcement to all members (SMS + in-app)."""
    cooperative_id = get_cooperative_id(request)
    if not cooperative_id and request.user.role != 'super_admin':
        django_messages.error(request, 'No cooperative selected')
        return redirect('core:dashboard')
    return render(request, 'notifications/broadcast.html')


@permission_required('notifications.send')
def notification_send(request):
    cooperative_id = get_cooperative_id(request)
    if not cooperative_id and request.user.role != 'super_admin':
        django_messages.error(request, 'No cooperative selected')
        return redirect('core:dashboard')

    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type', 'system')
        send_to = request.POST.get('send_to')
        send_sms = request.POST.get('send_sms') == 'yes'

        users = get_cooperative_users(cooperative_id, send_to)

        phone_list = []
        admin = request.user

        for user in users:
            Notification.objects.create(
                cooperative_id=cooperative_id,
                user_id=user.id,
                notification_type=notification_type,
                title=title,
                message=message,
                sent_via_sms=send_sms,
            )
            if send_sms and user.phone:
                phone_list.append(user.phone)

        # Create a broadcast conversation + message for in-app chat
        if users.count() > 0:
            conv = Conversation.objects.create(
                cooperative_id=cooperative_id,
                title=f'Announcement: {title[:50]}',
                is_group=True,
                created_by_id=admin.id,
            )
            participant_ids = set()
            for user in users:
                participant_ids.add(user.id)
            participant_ids.add(admin.id)
            for uid in participant_ids:
                ConversationParticipant.objects.get_or_create(
                    conversation=conv,
                    user_id=uid,
                )
            Message.objects.create(
                conversation=conv,
                sender_id=admin.id,
                content=f'[{title}]\n{message}',
            )

        # Send SMS
        if send_sms and phone_list:
            sms_text = f'MGOWELO AMCOS: {title}\n{message[:150]}'
            sent = broadcast_sms(phone_list, sms_text, cooperative_id)
            django_messages.success(request, f'Notification sent to {users.count()} users, SMS sent to {sent} numbers')
        else:
            django_messages.success(request, f'Notification sent to {users.count()} users')

        return redirect('notifications:list')

    return render(request, 'notifications/send.html')


# ─── Messaging / Chat ───────────────────────────────────────────────

@permission_required('notifications.inbox')
def inbox(request):
    cooperative_id = request.session.get('cooperative_id')
    participant_convs = ConversationParticipant.objects.filter(
        user_id=request.user.id
    ).values_list('conversation_id', flat=True)
    conversations = Conversation.objects.filter(id__in=participant_convs).prefetch_related('participants')
    conversation_data = []
    for conv in conversations:
        unread = Message.objects.filter(
            conversation=conv,
            is_read=False
        ).exclude(sender_id=request.user.id).count()
        conversation_data.append({'conv': conv, 'unread': unread})
    return render(request, 'notifications/inbox.html', {
        'conversation_data': conversation_data,
    })


@permission_required('notifications.inbox')
def conversation_view(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    is_participant = ConversationParticipant.objects.filter(
        conversation=conv, user_id=request.user.id
    ).exists()
    if not is_participant:
        django_messages.error(request, 'You are not a participant in this conversation')
        return redirect('notifications:inbox')

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                conversation=conv,
                sender_id=request.user.id,
                content=content,
            )
        return redirect('notifications:conversation', conversation_id=conv.id)

    messages_qs = conv.messages.select_related().all()
    # Mark messages as read
    Message.objects.filter(
        conversation=conv,
        is_read=False
    ).exclude(sender_id=request.user.id).update(
        is_read=True, read_at=timezone.now()
    )
    ConversationParticipant.objects.filter(
        conversation=conv, user_id=request.user.id
    ).update(last_read_at=timezone.now())

    participants = ConversationParticipant.objects.filter(conversation=conv)
    user_ids = [p.user_id for p in participants]
    users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}

    return render(request, 'notifications/conversation.html', {
        'conversation': conv,
        'messages': messages_qs,
        'participants': participants,
        'users_map': users_map,
    })


@permission_required('notifications.inbox')
def send_message(request):
    cooperative_id = get_cooperative_id(request)
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        content = request.POST.get('content')
        if not recipient_id or not content:
            django_messages.error(request, 'Recipient and message required')
            return redirect('notifications:new_message')

        if cooperative_id:
            recipient = get_object_or_404(User, id=recipient_id, cooperative_id=cooperative_id)
        else:
            recipient = get_object_or_404(User, id=recipient_id)
        admin = request.user

        # Find existing 1-on-1 conversation
        my_convs = ConversationParticipant.objects.filter(
            user_id=admin.id
        ).values_list('conversation_id', flat=True)
        their_convs = ConversationParticipant.objects.filter(
            user_id=recipient.id
        ).values_list('conversation_id', flat=True)
        common = set(my_convs) & set(their_convs)
        existing_conv = None
        for cid in common:
            conv = Conversation.objects.get(id=cid)
            if not conv.is_group and conv.participants.count() == 2:
                existing_conv = conv
                break

        if existing_conv:
            conv = existing_conv
        else:
            conv = Conversation.objects.create(
                cooperative_id=cooperative_id,
                is_group=False,
                created_by_id=admin.id,
            )
            ConversationParticipant.objects.get_or_create(conversation=conv, user_id=admin.id)
            ConversationParticipant.objects.get_or_create(conversation=conv, user_id=recipient.id)

        Message.objects.create(
            conversation=conv,
            sender_id=admin.id,
            content=content,
        )
        django_messages.success(request, 'Message sent')
        return redirect('notifications:conversation', conversation_id=conv.id)

    users = User.objects.all()
    if cooperative_id:
        users = users.filter(cooperative_id=cooperative_id)
    users = users.exclude(id=request.user.id)
    return render(request, 'notifications/new_message.html', {
        'users': users,
    })


