from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Basket, BasketItem
from .forms import BasketAddForm
from products.models import ProductVariant
from django.views import View
from django.http import JsonResponse

from wishlist.models import WishlistItem


# Create your views here.

# adding items to basket
class BasketAddView(View):
    def post(self, request, *args, **kwargs):
        form = BasketAddForm(request.POST)

        print("-" * 50)
        print("Received POST Data:", request.POST) # Is variant_id here?
        print("User Authenticated:", request.user.is_authenticated)
        

        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "error": "login_required"}, status=403)

        if form.is_valid():
            variant_id = form.cleaned_data['variant_id']
            quantity = form.cleaned_data['quantity']

            variant = get_object_or_404(ProductVariant, id=variant_id)
            product = variant.product


            # to prevent blocked/unlisted products
            if not product.is_listed or not product.category.is_active:
                return JsonResponse({
                    "success":False,
                    "error": "This product cannot be added to the cart."
                }, status=403)

            #remove from whishlist if exists and mark from_wishlist

            wishlist_item = WishlistItem.objects.filter(wishlist__user=request.user, variant=variant).first()
            if wishlist_item:
                wishlist_item.delete()
                from_wishlist = True
            else:
                from_wishlist = False

            # Get or create basket
            basket, _ = Basket.objects.get_or_create(user=request.user)

            # Add or update item
            item, created = BasketItem.objects.get_or_create(
                basket=basket,
                variant=variant,
                defaults={"quantity": quantity, "from_wishlist": from_wishlist},
            )

            if not created:

                # to limit the maximum quantity to add
                new_quantity = item.quantity + quantity
                if  new_quantity > variant.stock:
                    return JsonResponse({
                        "success" : False,
                        "error" :f"Only {variant.stock} items available in stock."
                    }, status=400)
                if new_quantity > variant.max_quantity_per_order:
                    return JsonResponse({
                        "success": False,
                        "error" : f"Maximum {variant.max_quantity_per_order} allowed per order."
                    }, status=400)
                item.quantity += quantity
                item.save()

            # Remove from wishlist if exists
            WishlistItem.objects.filter(wishlist__user=request.user, variant=variant).delete()

            image = variant.product.images.first()
            image_url = image.image.url if image else ""

            return JsonResponse({
                "success": True,
                "product": variant.product.name,
                "variant": str(variant),
                "quantity": item.quantity,
                "basket_count": basket.total_items,  # total items in basket
                "subtotal": basket.total_price,       # total price
                "image": image_url,
            })
        else:
            
            print("!!! FORM VALIDATION FAILED !!!")
            print("Form Errors (as_json):", form.errors.as_json())
        
            return HttpResponseBadRequest(f"Form Validation Failed. Errors: {form.errors.as_text()}", content_type="text/plain")

#removing item from basket

class BasketRemoveView(LoginRequiredMixin, View):

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

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            basket= get_object_or_404(Basket, user=request.user)
            items = basket.items.select_related('variant', 'variant__product').all()
            total_price = sum(item.subtotal for item in items)

        else:
            items = []
            total_price = 0

        context = {
            "basket": basket if request.user.is_authenticated else None,
            "items" : items,
            "total_price" : total_price,
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