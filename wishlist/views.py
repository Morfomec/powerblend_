from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Wishlist, WishlistItem
from basket.models import Basket, BasketItem
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
        messages.success(request, "Item removed from the wishlist.")
        return redirect(request.META.get("HTTP_REFERER", "/"))


class MoveToBasketView(LoginRequiredMixin, View):
    def post(self, request, variant_id, *args, **kwargs):
        variant = get_object_or_404(ProductVariant, id=variant_id)

        #get or create usr's basket
        basket, _ = Basket.objects.get_or_create(user=request.user)

        #add item to basket(if not there already)
        basket_item, created = BasketItem.objects.get_or_create(
            basket=basket,
            variant=variant,
            defaults = {'quantity':1, 'from_wishlist': True}
        )
        if not created:
            basket_item.quantity += 1
            basket_item.save()

        #remove from wishlist if present
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            WishlistItem.objects.filter(wishlist=wishlist, variant=variant).delete()

        messages.success(request, f"{variant.product.name} movied to basket.")
        return redirect(request.META.get("HTTP_REFERER", "/"))


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


