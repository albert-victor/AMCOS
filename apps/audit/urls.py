from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('trails/', views.audit_trails, name='trails'),
    path('compliance/', views.compliance_checks, name='compliance'),
    path('compliance/<int:check_id>/update/', views.compliance_update, name='compliance_update'),
    path('fraud-alerts/', views.fraud_alerts, name='fraud_alerts'),
]
