from django.urls import path
from . import views
from django.shortcuts import redirect
847

urlpatterns = [
    path("", views.home_view, name='home'),
    path("products_list", views.list_products, name="list_products"),
    path("product_detail/<int:id>/", views.detail_product, name="detail_product"),
    path('search_suggestions/', views.search_suggestions, name='search_suggestions'),
]