from django.urls import path
from .views import WishlistAddView, WishlistRemoveView, WishlistDetailView

urlpatterns = [
    path("", WishlistDetailView.as_view(), name='wishlist_view'),
    path("add/<int:variant_id>/", WishlistAddView.as_view(), name="wishlist_add"),
    path("remove/<int:variant_id>/", WishlistRemoveView.as_view(), name="wishlist_remove"),
]