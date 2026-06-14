from django.urls import path
from . import views

app_name = 'shares'

urlpatterns = [
    path('', views.share_list, name='list'),
    path('<int:share_id>/', views.share_detail, name='detail'),
    path('<int:share_id>/certificate/', views.share_certificate, name='certificate'),
    path('<int:share_id>/receipt/', views.share_receipt, name='receipt'),
    path('purchase/', views.share_purchase, name='purchase'),
    path('dividends/', views.dividend_list, name='dividends'),
]
