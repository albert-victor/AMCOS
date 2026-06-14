from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('send/', views.notification_send, name='send'),
    path('<int:notification_id>/read/', views.notification_mark_read, name='mark_read'),
    path('mark-all-read/', views.notification_mark_all_read, name='mark_all_read'),
    # Messaging
    path('inbox/', views.inbox, name='inbox'),
    path('inbox/<int:conversation_id>/', views.conversation_view, name='conversation'),
    path('new-message/', views.send_message, name='new_message'),
    path('broadcast/', views.broadcast, name='broadcast'),
]
