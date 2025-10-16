from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_offer_list, name='admin_offer_list'),
    path('add/', views.admin_add_offer, name='admin_add_offer'),
    path('edit/<int:offer_id>/', views.admin_edit_offer, name='admin_edit_offer'),
    path('delete/<int:offer_id>/', views.admin_delete_offer, name='admin_delete_offer'),
]