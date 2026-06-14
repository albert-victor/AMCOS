from django.contrib import admin
from .models import Meeting, MeetingAttendance, Resolution, Election, Candidate, Vote, MeetingDocument, MeetingComment


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'meeting_type', 'date', 'venue', 'status', 'created_at']
    list_filter = ['meeting_type', 'status', 'date']


@admin.register(MeetingAttendance)
class MeetingAttendanceAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'member_name', 'attended', 'check_in_time']


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ['title', 'meeting', 'is_passed', 'votes_for', 'votes_against', 'implemented']


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'status', 'voting_start', 'voting_end']
    list_filter = ['status']


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['member_name', 'election', 'is_approved', 'vote_count']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['election', 'candidate', 'member_id', 'voted_at']


@admin.register(MeetingDocument)
class MeetingDocumentAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'title', 'uploaded_at']


@admin.register(MeetingComment)
class MeetingCommentAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'author_name', 'author_role', 'created_at']
    list_filter = ['author_role', 'created_at']
