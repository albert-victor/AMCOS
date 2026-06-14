from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='list'),
    path('dashboard/', views.payment_dashboard, name='dashboard'),
    path('make/', views.payment_make, name='make'),
    path('submit-transaction/', views.payment_submit_transaction, name='submit_transaction'),
    path('<int:payment_id>/', views.payment_detail, name='detail'),
    path('<int:payment_id>/confirm/', views.payment_confirm, name='confirm'),
    path('<int:payment_id>/verify/', views.payment_verify, name='verify'),
    path('<int:payment_id>/receipt/', views.payment_receipt, name='receipt'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/generate/', views.invoice_generate, name='invoice_generate'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/print/', views.invoice_print, name='invoice_print'),
    path('invoices/<int:invoice_id>/pay/', views.invoice_pay, name='invoice_pay'),
]
