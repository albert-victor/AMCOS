from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_list, name='list'),
    path('apply/', views.loan_apply, name='apply'),
    path('products/', views.loan_products, name='products'),
    path('<int:loan_id>/', views.loan_detail, name='detail'),
    path('<int:loan_id>/review/', views.loan_review, name='review'),
    path('<int:loan_id>/disburse/', views.loan_disburse, name='disburse'),
    path('<int:loan_id>/repay/', views.loan_repayment_create, name='repay'),
    path('<int:loan_id>/schedule/', views.loan_schedule, name='schedule'),
    path('<int:loan_id>/statement/', views.loan_statement, name='statement'),
]
