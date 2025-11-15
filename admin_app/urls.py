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
    path('sales-report', views.sales_report, name='sales_report'), 
    path('sales-report/pdf/', views.download_pdf, name='download_pdf'),
    path('sales-report/excel/', views.download_excel, name='download_excel'),
    

    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.add_coupon, name='add_coupon'),
    path('coupons/edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('coupons/delete/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),

    path('banner/', views.admin_banner_list, name='admin_banner_list'),
    path('banner/add/', views.admin_banner_add, name='admin_banner_add'),
    path('banner/edit/<int:banner_id>/', views.admin_banner_edit, name='admin_banner_edit'),
    path('banner/delete/<int:banner_id>/', views.admin_banner_delete, name='admin_banner_delete'),
]

