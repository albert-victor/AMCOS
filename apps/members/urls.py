from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='list'),
    path('create/', views.member_create, name='create'),
    path('pending-registrations/', views.pending_registrations, name='pending_registrations'),
    path('<int:member_id>/registration-review/', views.registration_review, name='registration_review'),
    path('<int:member_id>/board-approve/', views.board_approve_member, name='board_approve'),
    path('<int:member_id>/', views.member_detail, name='detail'),
    path('<int:member_id>/mark-leader/', views.member_mark_leader, name='mark_leader'),
    path('<int:member_id>/remove-leader/', views.member_remove_leader, name='remove_leader'),
    path('<int:member_id>/approve/', views.member_approve, name='approve'),
    path('<int:member_id>/reject/', views.member_reject, name='reject'),
    path('<int:member_id>/suspend/', views.member_suspend, name='suspend'),
    path('<int:member_id>/documents/', views.kyc_documents, name='documents'),
    path('<int:member_id>/id-card/', views.member_id_card, name='id_card'),
    path('<int:member_id>/id-card/pdf/', views.member_id_card_pdf, name='id_card_pdf'),
    path('id-cards/bulk/', views.member_id_card_bulk, name='id_card_bulk'),
    path('id-cards/bulk/pdf/', views.member_id_card_bulk_pdf, name='id_card_bulk_pdf'),
    path('<int:member_id>/signature/', views.member_signature, name='signature'),
    path('<int:member_id>/record-card/', views.record_card_issuance, name='record_card'),
]
