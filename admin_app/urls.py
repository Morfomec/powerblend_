from django.urls import path
from . import views
# from django.shortcuts import redirect

urlpatterns = [
    path("", views.admin_login, name="admin_login"),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('user/', views.admin_user, name='admin_user'),
    path('toggle/<int:user_id>/', views.toggle_user_status,name='toggle_user_status'),
    path('settings/',views.admin_settings, name='admin_settings'),
]