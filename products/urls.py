from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_products, name='admin_products'),
    path("add/", views.add_product, name='add_product'),
    path("<int:product_id>/edit-product/", views.edit_product, name='edit_product'),
    path("<int:product_id>/delete-product/", views.delete_product, name='delete_product'),
    path("toggle/<int:product_id>/", views.toggle_product_listing, name='toggle_product_listing'),
    path("<int:product_id>/add-variant/", views.add_variants, name='add_variants'),
    path("<int:variant_id>/edit-variant/", views.edit_variant, name='edit_variant'),
    path("<int:variant_id>/delete-variant/", views.delete_variant, name='delete_variant'),
    path("<int:product_id>/attributes/", views.manage_attributes, name="manage_attributes"),
    path("toggle/<int:variant_id>/", views.toggle_variant_listing, name="toggle_variant_listing"),
    path("<int:image_id>/delete-image/", views.delete_product_image, name='delete_product_image'),
    path('upload-product-images', views.upload_product_images, name='upload_product_images'),
]
