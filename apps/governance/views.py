from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

from apps.core.utils import get_cooperative_id, get_obj_or_404_with_coop
from apps.core.permissions import permission_required, user_can
from apps.authentication.models import User
from apps.notifications.models import Notification

from .models import Meeting, MeetingAttendance, Resolution, Election, Candidate, Vote, MeetingDocument, MeetingComment

DEMO_MEETING_LINK = 'https://meet.google.com/abc-defg-hij'

JOIN_MEETING_ROLES = frozenset({
    'member', 'board_member', 'chairperson', 'vice_chairperson',
    'secretary', 'vice_secretary', 'parrc', 'treasurer',
    'accountant', 'loan_officer', 'auditor', 'carder', 'cooperative_admin',
})


def _resolve_cooperative_id(request):
    return get_cooperative_id(request) or getattr(request.user, 'cooperative_id', None)


def _user_can_join_meeting(user):
    from apps.authentication.leadership import is_board_leader, user_leadership_role
    if not user.is_authenticated:
        return False
    if user.role in JOIN_MEETING_ROLES:
        return True
    if is_board_leader(user):
        return True
    lr = user_leadership_role(user)
    return lr in JOIN_MEETING_ROLES


def _meeting_join_url(meeting):
    return (meeting.meeting_link or '').strip() or DEMO_MEETING_LINK


@permission_required('governance.view')
def meeting_list(request):
    cooperative_id = _resolve_cooperative_id(request)
    meetings = Meeting.objects.all().order_by('-date', '-start_time')
    if cooperative_id:
        meetings = meetings.filter(cooperative_id=cooperative_id)
    return render(request, 'governance/meetings.html', {
        'meetings': meetings,
        'can_manage': user_can(request.user, 'governance.manage'),
        'can_join_meeting': _user_can_join_meeting(request.user),
    })


@permission_required('governance.view')
def meeting_detail(request, meeting_id):
    meeting = get_obj_or_404_with_coop(Meeting, request, meeting_id)
    leader_roles = {'parrc', 'chairperson', 'secretary', 'board_member'}
    can_view_comments = request.user.is_authenticated and request.user.role in leader_roles
    can_post_comment = request.user.is_authenticated and request.user.role == 'member'
    return render(request, 'governance/meeting_detail.html', {
        'meeting': meeting,
        'attendance': meeting.attendance.all(),
        'resolutions': meeting.resolutions.all(),
        'documents': meeting.documents.all().order_by('-uploaded_at'),
        'can_manage': user_can(request.user, 'governance.manage'),
        'can_view_comments': can_view_comments,
        'can_post_comment': can_post_comment,
        'comments': meeting.comments.all().order_by('-created_at') if can_view_comments else MeetingComment.objects.none(),
        'can_join_meeting': _user_can_join_meeting(request.user),
        'meeting_join_url': _meeting_join_url(meeting) if _user_can_join_meeting(request.user) else '',
        'user_checked_in': meeting.attendance.filter(
            member_id=request.user.id, attended=True,
        ).exists() if request.user.is_authenticated else False,
    })


@permission_required('governance.view')
def meeting_comment_add(request, meeting_id):
    if request.method != 'POST':
        return redirect('governance:meeting_detail', meeting_id=meeting_id)

    if getattr(request.user, 'role', None) != 'member':
        messages.error(request, 'Huna ruhusa ya kutoa comment. / You cannot comment.')
        return redirect('core:dashboard')

    meeting = get_obj_or_404_with_coop(Meeting, request, meeting_id)
    body = request.POST.get('comment_text', '').strip()
    if not body:
        messages.warning(request, 'Andika comment kwanza. / Enter your comment.')
        return redirect('governance:meeting_detail', meeting_id=meeting_id)

    MeetingComment.objects.create(
        meeting=meeting,
        author_user_id=request.user.id,
        author_role=request.user.role,
        author_name=request.user.get_full_name() or request.user.username,
        body=body,
    )
    messages.success(request, 'Ujumbe wako umepokelewa. / Your comment was received.')
    return redirect('governance:meeting_detail', meeting_id=meeting_id)


@permission_required('governance.manage')
def meeting_create(request):
    if request.method == 'POST':
        cooperative_id = _resolve_cooperative_id(request)
        if not cooperative_id:
            messages.error(request, 'Hakuna ushirika uliochaguliwa. / No cooperative assigned.')
            return redirect('governance:meetings')
        meeting = Meeting.objects.create(
            cooperative_id=cooperative_id,
            title=request.POST.get('title'),
            meeting_type=request.POST.get('meeting_type'),
            description=request.POST.get('description', ''),
            venue=request.POST.get('venue'),
            date=request.POST.get('date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            agenda=request.POST.get('agenda', ''),
            meeting_link=(request.POST.get('meeting_link') or '').strip() or 'https://meet.google.com/abc-defg-hij',
            organized_by=request.user.id,
        )
        users = User.objects.filter(cooperative_id=cooperative_id, is_active=True)
        detail_link = reverse('governance:meeting_detail', args=[meeting.id])
        use_sw = str(getattr(settings, 'LANGUAGE_CODE', 'en')).lower().startswith('sw')
        if use_sw:
            title = 'Mkutano Mpya Umewekwa'
            body = f'Mkutano "{meeting.title}" umewekwa tarehe {meeting.date}. Bofya kuona maelezo na kuhudhuria.'
        else:
            title = 'New Meeting Scheduled'
            body = f'"{meeting.title}" is scheduled for {meeting.date}. Open to view details and attend.'
        for u in users:
            Notification.objects.create(
                cooperative_id=cooperative_id,
                user_id=u.id,
                notification_type='meeting',
                priority='normal',
                title=title,
                message=body,
                link=detail_link,
            )
        messages.success(request, 'Meeting created successfully')
        return redirect('governance:meetings')
    return render(request, 'governance/meeting_form.html')


@permission_required('governance.view')
def meeting_join(request, meeting_id):
    if request.method != 'POST':
        return redirect('governance:meeting_detail', meeting_id=meeting_id)
    meeting = get_obj_or_404_with_coop(Meeting, request, meeting_id)
    user = request.user
    attendance, _ = MeetingAttendance.objects.get_or_create(
        meeting=meeting,
        member_id=user.id,
        defaults={
            'member_name': user.get_full_name() or user.username,
        },
    )
    from apps.authentication.leadership import user_leadership_role
    lr = user_leadership_role(user)
    attendance.member_name = user.get_full_name() or user.username
    attendance.attendee_phone = user.phone or ''
    attendance.attendee_role = lr or user.role or ''
    attendance.attended = True
    attendance.check_in_time = timezone.now()
    attendance.notes = f'Joined by {user.username}'
    attendance.save()
    join_url = _meeting_join_url(meeting)
    if join_url:
        return redirect(join_url)
    messages.success(request, 'Mahudhurio yamerekodiwa.')
    return redirect('governance:meeting_detail', meeting_id=meeting.id)


@permission_required('governance.manage')
def meeting_minutes(request, meeting_id):
    meeting = get_obj_or_404_with_coop(Meeting, request, meeting_id)
    if request.method == 'POST':
        minutes_text = request.POST.get('minutes', '').strip()
        if minutes_text:
            meeting.minutes = minutes_text

        uploaded_files = request.FILES.getlist('documents')
        doc_title = request.POST.get('document_title', '').strip()
        for idx, f in enumerate(uploaded_files):
            title = doc_title or f.name
            if len(uploaded_files) > 1 and doc_title:
                title = f'{doc_title} ({idx + 1})'
            MeetingDocument.objects.create(
                meeting=meeting,
                title=title,
                file=f,
                description=request.POST.get('document_description', ''),
            )

        if minutes_text or uploaded_files:
            meeting.minutes_uploaded_at = timezone.now()
            if meeting.status in ('scheduled', 'in_progress'):
                meeting.status = 'completed'
            meeting.save()
            messages.success(
                request,
                'Dakika/nyaraka zimehifadhiwa na zinaonekana kwa wanachama. / '
                'Minutes/documents saved and visible to members.',
            )
        else:
            messages.warning(request, 'Andika dakika au pakia faili. / Enter minutes or upload a file.')
        return redirect('governance:meeting_detail', meeting_id=meeting.id)

    return render(request, 'governance/meeting_minutes.html', {
        'meeting': meeting,
        'documents': meeting.documents.all().order_by('-uploaded_at'),
    })


@permission_required('governance.view')
def election_list(request):
    if getattr(request.user, 'role', None) == 'board_member':
        return redirect('core:dashboard')
    cooperative_id = _resolve_cooperative_id(request)
    elections = Election.objects.all()
    if cooperative_id:
        elections = elections.filter(cooperative_id=cooperative_id)
    return render(request, 'governance/elections.html', {'elections': elections})


@permission_required('governance.view')
def election_detail(request, election_id):
    if getattr(request.user, 'role', None) == 'board_member':
        return redirect('core:dashboard')
    election = get_obj_or_404_with_coop(Election, request, election_id)
    return render(request, 'governance/election_detail.html', {
        'election': election,
        'candidates': election.candidates.all(),
    })


@permission_required('governance.manage')
def election_create(request):
    if request.method == 'POST':
        cooperative_id = _resolve_cooperative_id(request)
        if not cooperative_id:
            messages.error(request, 'Hakuna ushirika uliochaguliwa. / No cooperative assigned.')
            return redirect('governance:elections')
        Election.objects.create(
            cooperative_id=cooperative_id,
            title=request.POST.get('title'),
            position=request.POST.get('position'),
            description=request.POST.get('description', ''),
            nomination_start=request.POST.get('nomination_start'),
            nomination_end=request.POST.get('nomination_end'),
            voting_start=request.POST.get('voting_start'),
            voting_end=request.POST.get('voting_end'),
            created_by=request.user.id,
        )
        messages.success(request, 'Election created successfully')
        return redirect('governance:elections')
    return render(request, 'governance/election_form.html')


@permission_required('governance.vote')
def vote_cast(request, election_id):
    election = get_obj_or_404_with_coop(Election, request, election_id)

    if Vote.objects.filter(election=election, member_id=request.user.member_id).exists():
        messages.error(request, 'You have already voted')
        return redirect('governance:election_detail', election_id=election.id)

    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')
        candidate = get_object_or_404(Candidate, id=candidate_id, election=election)

        Vote.objects.create(
            election=election,
            candidate=candidate,
            member_id=request.user.member_id or request.user.id,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        candidate.vote_count += 1
        candidate.save()

        messages.success(request, 'Vote cast successfully')
        return redirect('governance:election_detail', election_id=election.id)

    return render(request, 'governance/vote.html', {'election': election})
