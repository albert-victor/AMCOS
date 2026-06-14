"""Member registration notifications and board workflow helpers."""
from django.urls import reverse
from django.conf import settings

from apps.authentication.models import User
from apps.notifications.models import Notification

from .member_access import BOARD_APPROVALS_REQUIRED, sync_member_status_after_board_approval


def notify_board_new_registration(member):
    """Alert all board members in the cooperative about a new registration."""
    from apps.authentication.leadership import board_approver_queryset
    board_users = board_approver_queryset(member.cooperative_id)
    link = reverse('members:registration_review', args=[member.id])
    use_sw = str(getattr(settings, 'LANGUAGE_CODE', 'en')).lower().startswith('sw')
    if use_sw:
        title = 'Mwanachama Mpya Amesajiliwa'
        message = (
            f'{member.full_name} amejisajili na kulipa ada. '
            f'Angalia maombi na uidhinishe ikiwa anastahili (ekari: {member.hectares or "—"}).'
        )
    else:
        title = 'New Member Registered'
        message = (
            f'{member.full_name} has registered and paid the entry fee. '
            f'Review and approve if eligible (hectares: {member.hectares or "—"}).'
        )
    for user in board_users:
        Notification.objects.create(
            cooperative_id=member.cooperative_id,
            user_id=user.id,
            notification_type='approval',
            priority='high',
            title=title,
            message=message,
            link=link,
        )


def notify_leadership_elected(member, elected_by=None):
    """Notify all active cooperative users that a member was elected to board leadership."""
    cooperative_id = member.cooperative_id
    if not cooperative_id:
        return 0

    elector_name = ''
    if elected_by and getattr(elected_by, 'is_authenticated', False):
        elector_name = elected_by.get_full_name() or elected_by.username

    link = reverse('members:detail', args=[member.id])
    use_sw = str(getattr(settings, 'LANGUAGE_CODE', 'en')).lower().startswith('sw')
    if use_sw:
        title = 'Mjumbe Mpya wa Bodi Ameteuliwa'
        if elector_name:
            message = (
                f'{member.full_name} ameteuliwa mjumbe wa bodi na {elector_name}. '
                f'Bofya kuona wasifu wake.'
            )
        else:
            message = (
                f'{member.full_name} ameteuliwa mjumbe wa bodi. '
                f'Bofya kuona wasifu wake.'
            )
    else:
        title = 'New Board Member Elected'
        if elector_name:
            message = (
                f'{member.full_name} has been elected as a board member by {elector_name}. '
                f'Open their profile for details.'
            )
        else:
            message = (
                f'{member.full_name} has been elected as a board member. '
                f'Open their profile for details.'
            )

    recipients = User.objects.filter(
        cooperative_id=cooperative_id,
        is_active=True,
    )
    notifications = [
        Notification(
            cooperative_id=cooperative_id,
            user_id=user.id,
            notification_type='election',
            priority='high',
            title=title,
            message=message,
            link=link,
        )
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)


def record_board_approval(member, approver_user_id, notes=''):
    from .models import MemberBoardApproval

    approval, created = MemberBoardApproval.objects.get_or_create(
        member=member,
        approver_user_id=approver_user_id,
        defaults={'notes': notes},
    )
    if not created and notes:
        approval.notes = notes
        approval.save(update_fields=['notes'])
    sync_member_status_after_board_approval(member)
    member.refresh_from_db()

    if member.user_id:
        if member.status == 'approved':
            use_sw = str(getattr(settings, 'LANGUAGE_CODE', 'en')).lower().startswith('sw')
            Notification.objects.create(
                cooperative_id=member.cooperative_id,
                user_id=member.user_id,
                notification_type='approval',
                priority='high',
                title='Idhini ya Bodi Imekamilika' if use_sw else 'Board Approval Complete',
                message='Bodi imekubali usajili wako.' if use_sw else 'Board approved your registration.',
                link=reverse('shares:purchase'),
            )
    return approval, created
