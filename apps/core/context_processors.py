from django.conf import settings
from django.db import DatabaseError, OperationalError

from .models import SystemSetting
from django.db.models import Q


def system_settings(request):
    return {
        'system_name': 'Mkuu wa Mkoa - Enterprise Cooperative Management System',
        'system_version': '1.0.0',
        'current_year': 2026,
    }


def cooperative_info(request):
    from apps.cooperative.models import Cooperative
    context = {
        'current_cooperative': None,
        'cooperative_name': '',
        'cooperative_id': None,
        'user_role': None,
    }
    if request.user.is_authenticated:
        cooperative_id = request.session.get('cooperative_id')
        context['cooperative_id'] = cooperative_id
        context['user_role'] = getattr(request.user, 'role', None)
        if cooperative_id:
            try:
                coop = Cooperative.objects.get(id=cooperative_id)
                context['cooperative_name'] = coop.name
                context['current_cooperative'] = coop
            except (Cooperative.DoesNotExist, OperationalError, DatabaseError):
                pass
    return context


def rbac_permissions(request):
    from .permissions import build_permission_cache
    return {'rbac_cache': build_permission_cache(request.user)}


def database_mode(request):
    mode = getattr(settings, 'ACTIVE_DB_MODE', 'primary')
    status = getattr(settings, 'DB_STATUS', {})
    return {
        'db_active_mode': mode,
        'db_status_message': status.get('message', ''),
        'db_in_fallback': mode == 'fallback',
    }


def language_preference(request):
    from .lang import get_request_lang
    return {'current_lang': get_request_lang(request)}


def member_lifecycle(request):
    """Expose member onboarding stage for restricted dashboard UI."""
    from apps.authentication.leadership import is_board_leader
    context = {
        'member_lifecycle_stage': None,
        'member_is_restricted': False,
        'member_board_approvals': 0,
        'member_board_required': 5,
        'is_board_leader': False,
        'user_leadership_role': '',
    }
    if not request.user.is_authenticated:
        return context
    context['is_board_leader'] = is_board_leader(request.user)
    context['user_leadership_role'] = getattr(request.user, 'leadership_role', '') or ''
    if getattr(request.user, 'role', None) != 'member':
        return context
    try:
        from apps.core.member_utils import resolve_member_for_user
        from apps.members.member_access import (
            BOARD_APPROVALS_REQUIRED,
            board_approval_count,
            get_member_lifecycle_stage,
            is_restricted_member,
        )
        cooperative_id = request.session.get('cooperative_id') or request.user.cooperative_id
        member = resolve_member_for_user(request.user, cooperative_id)
        if member:
            context['member_lifecycle_stage'] = get_member_lifecycle_stage(member)
            context['member_is_restricted'] = is_restricted_member(member)
            context['member_board_approvals'] = board_approval_count(member)
            context['member_board_required'] = BOARD_APPROVALS_REQUIRED
    except (OperationalError, DatabaseError):
        pass
    return context


def notifications_count(request):
    context = {
        'unread_notifications_count': 0,
        'unread_messages_count': 0,
    }
    if request.user.is_authenticated:
        try:
            from apps.notifications.models import Notification, Message, ConversationParticipant
            context['unread_notifications_count'] = Notification.objects.filter(
                user_id=request.user.id, is_read=False
            ).count()
            user_convs = ConversationParticipant.objects.filter(
                user_id=request.user.id
            ).values_list('conversation_id', flat=True)
            context['unread_messages_count'] = Message.objects.filter(
                conversation_id__in=user_convs,
                is_read=False
            ).exclude(sender_id=request.user.id).count()
        except (OperationalError, DatabaseError):
            pass
    return context
