from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_products, name='admin_products'),
    path("products/add/", views.add_product, name='add_product'),

]