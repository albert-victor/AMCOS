from django.urls import path
from . import views

app_name = 'savings'

urlpatterns = [
    path('', views.account_list, name='list'),
    path('create/', views.account_create, name='create'),
    path('<int:account_id>/', views.account_detail, name='detail'),
    path('<int:account_id>/deposit/', views.transaction_deposit, name='deposit'),
    path('<int:account_id>/withdraw/', views.transaction_withdraw, name='withdraw'),
    path('<int:account_id>/statement/', views.account_statement, name='statement'),
]
