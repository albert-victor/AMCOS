from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('settings/', views.system_settings, name='system_settings'),
    path('set-lang/', views.set_language_view, name='set_language'),
    path('db-status/', views.database_status_page, name='database_status'),
]
