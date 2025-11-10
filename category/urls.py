from django.urls import path
from . import views
# from django.shortcuts import redirect

urlpatterns = [
    path("", views.admin_category, name='admin_category'),
    path("add/", views.add_category, name='add_category'),
    path("<int:category_id>/edit/", views.edit_category, name='edit_category'),
    path("<int:category_id>/delete/", views.delete_category, name="delete_category"),
    path("toggle/<int:category_id>/", views.toggle_category_listing, name='toggle_category_listing'),
]