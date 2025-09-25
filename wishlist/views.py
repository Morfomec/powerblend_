from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Wishlist, WishlistItem
from products.models import ProductVariant

# Create your views here.

class WishlistAddView(LoginRequiredMixin, View):
    
    def post(self, request, variant_id, *args, **kwargs):
        variant = get_object_or_404(ProductVariant, id=variant_id)

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

        item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, variant=variant)

        if created:
            messages.success(request, f"{variant.product.name} added to wishlist.")
        
        else:
            item.delete()
            messages.info(request, f"{variant.product.name} is already in your wishlists.")

        return redirect(request.META.get("HTTP_REFERER", "wishlist_view"))


class WishlistRemoveView(LoginRequiredMixin, View):

    def post(self, request, variant_id, *args, **kwargs):
        wishlist = get_object_or_404(Wishlist, user=request.user)
        item = get_object_or_404(WishlistItem, wishlist=wishlist, variant_id=variant_id)
        item.delete()
        messages.success(request, "Item remove from the wishlist.")
        return redirect(request.MET.get("HTTP_REFERER", "/"))


class WishlistDetailView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return render(request, "wishlist.html", {"items": []})


        wishlist,_ = Wishlist.objects.get_or_create(user=request.user)
        items = wishlist.items.select_related("variant", "variant__product")
        context = {
            "wishlist":wishlist, 
            "items" : items
        }

        return render(request, "wishlist.html", context)

