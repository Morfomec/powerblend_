from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path("success/<int:order_id>/", views.order_success, name='order_success'),
    path('<int:order_id>/', views.order_details, name='order_details'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('cancel-item/<int:order_id>/',views.cancel_item, name='cancel_item'),
    path('return-item/<int:order_id>/',views.return_item, name='return-item'),
    # path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),

    path('admin/orders/', views.admin_order_list, name='admin_order_list'),
    path('admin/orders/<int:id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/<int:id>/update-status/', views.admin_update_order_status, name='admin_update_order_status'),

]