from django.shortcuts import get_object_or_404
from django.http import Http404


def get_cooperative_id(request):
    if request.user.is_authenticated and request.user.role == 'super_admin':
        return None
    cid = request.session.get('cooperative_id')
    if not cid and request.user.is_authenticated:
        cid = getattr(request.user, 'cooperative_id', None)
        if cid:
            request.session['cooperative_id'] = cid
    return cid


def get_coop_filter_kwargs(request, extra_filter=None):
    coop_id = get_cooperative_id(request)
    if coop_id:
        filter_kwargs = {'cooperative_id': coop_id}
    else:
        filter_kwargs = {}
    if extra_filter:
        filter_kwargs.update(extra_filter)
    return filter_kwargs


def get_obj_or_404_with_coop(model, request, lookup_id, lookup_field='id'):
    coop_id = get_cooperative_id(request)
    kwargs = {lookup_field: lookup_id}
    if coop_id:
        kwargs['cooperative_id'] = coop_id
    obj = get_object_or_404(model, **kwargs)
    assert_record_access(request, obj)
    return obj


def assert_record_access(request, obj):
    """Multi-tenant + member self-service guard."""
    coop_id = get_cooperative_id(request)
    if coop_id and getattr(obj, 'cooperative_id', None) not in (None, coop_id):
        raise Http404

    if getattr(request.user, 'role', None) == 'member':
        from apps.core.member_utils import get_request_member
        member = get_request_member(request)
        user_member_id = member.id if member else getattr(request.user, 'member_id', None)
        member_id = getattr(obj, 'member_id', None)
        user_id = getattr(obj, 'user_id', None)
        if member_id is not None and user_member_id and member_id != user_member_id:
            raise Http404
        if user_id is not None and user_id != request.user.id:
            raise Http404


def scope_member_queryset(queryset, request, member_field='member_id'):
    """Filter queryset to current member when role is member."""
    if getattr(request.user, 'role', None) != 'member':
        return queryset
    from apps.core.member_utils import get_request_member
    member = get_request_member(request)
    if not member:
        return queryset.none()
    return queryset.filter(**{member_field: member.id})
