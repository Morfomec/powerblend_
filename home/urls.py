from django.urls import path
from . import views
from django.shortcuts import redirect


urlpatterns = [
    path("", views.home_view, name='home'),
    path("product_list", views.list_products, name="list_products"),
    
]