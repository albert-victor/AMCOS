from django import template

from apps.core.permissions import user_can

register = template.Library()


@register.simple_tag(takes_context=True)
def can(context, permission_key):
    """{% can 'members.approve' as ok %}{% if ok %}...{% endif %}"""
    user = context.get('user')
    if not user or not user.is_authenticated:
        return False
    cache = context.get('rbac_cache')
    if cache is not None and permission_key in cache:
        return cache[permission_key]
    return user_can(user, permission_key)


@register.filter
def can_do(user, permission_key):
    """{{ user|can_do:'payments.verify' }}"""
    if not user or not user.is_authenticated:
        return False
    return user_can(user, permission_key)
