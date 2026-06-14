from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'auth'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('register/cooperative/', RedirectView.as_view(pattern_name='home', permanent=True)),
    path('verify-otp/', RedirectView.as_view(pattern_name='auth:login', permanent=False)),
    path('resend-otp/', RedirectView.as_view(pattern_name='auth:login', permanent=False)),
    path('register/member/', views.register_member, name='register_member'),
    path('terms/', views.terms_and_conditions, name='terms'),
    path('login/', views.login_view, name='login'),
    path('force-password-change/', views.force_password_change, name='force_password_change'),
    path('profile/', views.user_profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
]
