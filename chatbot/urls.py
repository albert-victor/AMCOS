from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('api/', views.chat_api, name='api'),
]
