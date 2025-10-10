from django.urls import path
from .views import WishlistAddView, WishlistRemoveView, WishlistDetailView, MoveToBasketView

urlpatterns = [
    path("", WishlistDetailView.as_view(), name='wishlist_view'),
    path("add/<int:variant_id>/", WishlistAddView.as_view(), name="wishlist_add"),
    path("remove/<int:variant_id>/", WishlistRemoveView.as_view(), name="wishlist_remove"),
    path("move-to-basket/<int:variant_id>/", MoveToBasketView.as_view(), name="move_to_basket"),
]