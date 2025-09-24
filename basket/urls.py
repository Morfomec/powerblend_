from django.urls import path
from . import views

# app_name = "basket"

urlpatterns=[
    path("", views.BasketDetailView.as_view(), name='basket_view'),
    path("add/", views.BasketAddView.as_view(), name="basket_add"),
    path("remove/<int:variant_id>/", views.BasketRemoveView.as_view(), name="basket_remove"),
    path("update/<int:item_id>", views.BasketUpdateView.as_view(), name="basket_update_item"),
]
