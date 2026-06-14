from django.urls import path
from . import views

app_name = 'governance'

urlpatterns = [
    path('meetings/', views.meeting_list, name='meetings'),
    path('meetings/create/', views.meeting_create, name='meeting_create'),
    path('meetings/<int:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:meeting_id>/join/', views.meeting_join, name='meeting_join'),
    path('meetings/<int:meeting_id>/minutes/', views.meeting_minutes, name='meeting_minutes'),
    path('meetings/<int:meeting_id>/comment/', views.meeting_comment_add, name='meeting_comment_add'),
    path('elections/', views.election_list, name='elections'),
    path('elections/create/', views.election_create, name='election_create'),
    path('elections/<int:election_id>/', views.election_detail, name='election_detail'),
    path('elections/<int:election_id>/vote/', views.vote_cast, name='vote'),
]
