from django.urls import path
from . import views

app_name = 'cooperative'

urlpatterns = [
    path('profile/', views.cooperative_profile, name='profile'),
    path('branches/', views.branches, name='branches'),
    path('branches/create/', views.branch_create, name='branch_create'),
    path('create/', views.cooperative_create_superadmin, name='create'),
    path('<int:cooperative_id>/edit/', views.cooperative_edit, name='edit'),
    path('<int:cooperative_id>/toggle-status/', views.cooperative_toggle_status, name='toggle_status'),
    path('<int:cooperative_id>/delete/', views.cooperative_delete, name='delete'),
]
