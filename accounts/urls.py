from django.urls import path
from . import views
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

urlpatterns = [
    # path("", views.home_view, name='home'),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name='login'),
    # path("includes/header/", views.home_view, name='header'),
    path("logout/", views.logout_view, name='logout'),
    path("forgot_password/", views.forgot_password, name="forgot_password"),
    path("verify_otp/", views.verify_otp_view, name='verify_otp'),
    path("resend_otp/", views.resend_otp, name='resend_otp'),


    #reset password urls 
    #  path('change-password/', auth_views.PasswordChangeView.as_view(template_name='change-password.html'),),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),

]