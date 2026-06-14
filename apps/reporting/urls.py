from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    path('', views.report_dashboard, name='dashboard'),
    path('members/', views.member_report, name='members'),
    path('savings/', views.savings_report, name='savings'),
    path('loans/', views.loan_report, name='loans'),
    path('payments/', views.payment_report, name='payments'),
]
