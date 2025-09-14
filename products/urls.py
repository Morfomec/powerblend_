from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_products, name='admin_products'),
    path("add/", views.add_product, name='add_product'),
    path("<int:product_id>/edit/", views.edit_product, name='edit_product'),
    path("<int:product_id>/delete/", views.delete_product, name='delet_product'),
    path("toggle/<int:product_id>/", views.toggle_product_listing, name='toggle_product_listing'),
    # path("varitans/", views.variants_product, name='variants_product'),
]