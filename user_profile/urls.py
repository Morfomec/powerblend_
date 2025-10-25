from django.urls import path
from . import views
# from django.shortcuts import redirect

urlpatterns = [
    path("", views.user_profile_view, name='user_profile_view'),

    path("dashboard/", views.user_dashboard, name='user_dashboard'),
    path("edit-profile/", views.edit_profile, name='edit_profile'),
    path("verify-email-otp/", views.verify_email_otp, name='verify_email_otp'),

    path("change-password/", views.change_password, name='change_password'),
    path("change-email/", views.change_email, name='change_email'),

    path("address/", views.address_view, name='address_list'),
    path("new/", views.address_create, name="address_create"),
    path("address/<int:id>/edit/", views.address_update, name="address_update"),
    path("address/<int:id>/delete/", views.address_delete, name="address_delete"),
    path('address<int:id>/set-default/', views.address_set_default, name='address_set_default'),

]