from django.urls import path
from . import views
# from django.shortcuts import redirect

urlpatterns = [
    path("", views.user_profile_view, name='user_profile_view'),
    path("address/", views.address_view, name='address_list'),
    path("new/", views.address_create, name="address_create"),
    path("address/<int:id>/edit/", views.address_update, name="address_update"),
    path("address/<int:id>/delete/", views.address_delete, name="address_delete"),
    path('address<int:id>/set-default/', views.address_set_default, name='address_set_default'),

]