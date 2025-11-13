from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Basket, BasketItem
from .forms import BasketAddForm
from products.models import ProductVariant
from django.views import View
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from wishlist.models import WishlistItem
from user_profile.models import Address
from offers.utils import get_best_offer_for_product, get_discount_info_for_variant


# Create your views here.

class BasketAddView(View):
    """
    adding items to the basket
    """
    def post(self, request, *args, **kwargs):

        form = BasketAddForm(request.POST)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({"success":False, "login_required":True})
            messages.warning(request, "Please log in to add items to your basket.")
            return redirect("account_login") 

        if form.is_valid():
            variant_id = form.cleaned_data["variant_id"]
            quantity = form.cleaned_data["quantity"]

            variant = get_object_or_404(ProductVariant, id=variant_id)
            product = variant.product

            # Prevent unlisted or blocked products
            if not product.is_listed or not product.category.is_active:
                if is_ajax:
                    return JsonResponse({"success":False, "error": "This product cannot be added to the basket."})
                
                messages.error(request, "This product cannot be added to the basket.")
                return redirect("detail_product",id=product.id)

            # Remove from wishlist if exists
            WishlistItem.objects.filter(wishlist__user=request.user, variant=variant).delete()

            basket, _ = Basket.objects.get_or_create(user=request.user)
            item, created = BasketItem.objects.get_or_create(
                basket=basket,
                variant=variant,
                defaults={"quantity": quantity},
            )

            if not created:
                new_quantity = item.quantity + quantity
                if new_quantity > variant.stock:

                    if is_ajax:
                        return JsonResponse({"success":False, "error": f"Only {variant.stock} items available in stock."})
                    messages.error(request, f"Only {variant.stock} items available in stock.")
                    return redirect("detail_product", id=product.id)

                item.quantity = new_quantity
                item.save()

            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "product": product.name,
                    "variant": str(variant),
                    "quantity": quantity,
                    "subtotal": basket.total_price, 
                    "basket_count": basket.items.count(),
                    "image": (
                        (variant.product.images.filter(is_primary=True).first() or variant.product.images.first()).image.url
                        if variant.product.images.exists()
                        else ""
                    ),

                })

            messages.success(request, f"{product.name} ({variant}) added to your basket!")
            return redirect("basket_view") 

        # Invalid form case
        if is_ajax:
            return JsonResponse({"success": False, "error": "Invalid data."}, status=400)
        messages.error(request, "Invalid data. Please try again.")
        return HttpResponseBadRequest("Form validation failed.")


class BasketRemoveView(LoginRequiredMixin, View):
    """
    remove items from the basket
    """

    def post(self, request, variant_id, *args, **kwargs):
        basket = get_object_or_404(Basket, user=request.user)
        item = get_object_or_404(BasketItem, basket=basket, variant_id=variant_id)
        
        #if an item came from wishlist it should go back if removing
        if item.from_wishlist:
            from wishlist.models import Wishlist, WishlistItem
            wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
            WishlistItem.objects.get_or_create(wishlist=wishlist, variant=item.variant)


        item.delete()
        messages.success(request, "Item removed from the basket.")
        
        

        
        return redirect(request.META.get('HTTP_REFERER', '/'))


#Basket datails view all items
class BasketDetailView(LoginRequiredMixin, View):
    """
    list items in the basket
    """

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # basket= get_object_or_404(Basket, user=request.user)
            basket, created = Basket.objects.get_or_create(user=request.user)
            items = basket.items.select_related('variant', 'variant__product').all()

            for item in items:
                item.variant.discount_info = get_discount_info_for_variant(item.variant)
                item.discounted_subtotal = item.variant.discount_info['price'] * item.quantity
                item.original_subtotal = item.variant.discount_info['original_price'] * item.quantity
                item.save_subtotal = item.variant.discount_info['save_price'] * item.quantity
                item.total_each_price = item.price * item.quantity

            total_price = sum(item.discounted_subtotal for item in items)

        else:
            basket = None
            items = []
            total_price = 0

        default_address = Address.objects.filter(user=request.user, is_default=True).first()
        context = {
            "basket": basket if request.user.is_authenticated else None,
            "items" : items,
            "total_price" : total_price,
            "default_address": default_address,
            "show_login_modal" : request.GET.get('show_login_modal', False)
        }

        return render(request, 'basket.html', context)


class BasketUpdateView(LoginRequiredMixin, View):
    """
    Updated the quantity of a basket item (+/-)
    """
    def get(self, request, *args, **kwargs):

         # Fetch item_id from kwargs
        item_id = kwargs.get('item_id')

        #fetch the basket item for the logged in users
        item = get_object_or_404(BasketItem, id=item_id, basket__user=request.user)

        action = request.GET.get('action')

        if action == 'increase':

            if item.quantity + 1 > item.variant.stock:
                messages.error(request, "Not enough stock.")
            elif item.quantity + 1 > item.variant.max_quantity_per_order:
                messages.error(request, f"Max {item.variant.max_quantity_per_order} allowed.")
            else:
                item.quantity += 1
                item.save()
        elif action == 'decrease' and item.quantity > 1:
            item.quantity -= 1
            item.save()
        
        data = {
            'quantity' : item.quantity,
            'subtotal' : item.subtotal,
            'total' : item.basket.total_price,
        }
        return redirect('basket_view')
        # return JsonResponse(data)


@login_required
@require_POST
def basket_update_item(request, item_id):
    """
    to update the items in the basket
    """

    try:
        data = json.loads(request.body)
        action = data.get("action")  


        item = BasketItem.objects.get(id=item_id, basket__user=request.user)

        # ✅ Update quantity safely
        if action == "increase" and item.quantity < item.variant.stock:
            item.quantity += 1
        elif action == "decrease" and item.quantity > 1:
            item.quantity -= 1
        item.save()

        # ✅ Reapply discount info for consistent logic
        discount_info = get_discount_info_for_variant(item.variant)
        discounted_price = discount_info["price"]
        original_price = discount_info.get("original_price", discounted_price)
        discount_percent = discount_info.get("discount_percent", 0)
        save_amount = discount_info.get("save_amount", 0)

        # ✅ Calculate subtotals using the discounted price
        discounted_subtotal = discounted_price * item.quantity
        original_subtotal = original_price * item.quantity
        save_subtotal = save_amount * item.quantity

        # ✅ Calculate basket total with discounts applied
        basket_items = BasketItem.objects.filter(basket__user=request.user)
        basket_total = sum(
            get_discount_info_for_variant(i.variant)["price"] * i.quantity for i in basket_items
        )

        return JsonResponse({
            "success": True,
            "new_quantity": item.quantity,
            "item_id": item.id,
            "basket_total": float(basket_total),
            "item_total": float(discounted_subtotal),  
            "per_piece_price": float(discounted_price), 
            "original_subtotal": float(original_subtotal),
            "save_subtotal": float(save_subtotal),
            "discount_percent": discount_percent,
            "stock": item.variant.stock,
        })
    except BasketItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Item not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})