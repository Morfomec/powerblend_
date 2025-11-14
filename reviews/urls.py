from django.urls import path
from . import views

urlpatterns = [
    path("review/<int:variant_id>/add/", views.submit_review, name="submit_review"),
]