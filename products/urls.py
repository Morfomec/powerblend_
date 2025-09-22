from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_products, name='admin_products'),
    path("add/", views.add_product, name='add_product'),
    path("<int:product_id>/edit/", views.edit_product, name='edit_product'),
    path("<int:product_id>/delete/", views.delete_product, name='delete_product'),
    path("toggle/<int:product_id>/", views.toggle_product_listing, name='toggle_product_listing'),
    path("<int:product_id>/variants/", views.add_variants, name='add_variants'),
    path("<int:product_id>/attributes/", views.manage_attributes, name="manage_attributes"),
    path("variant/toggle/<int:productvariant_id>/", views.toggle_variant_listing, name="toggle_variant_listing"),
]
