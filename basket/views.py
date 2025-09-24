from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Basket, BasketItem
from .forms import BasketAddForm
from products.models import ProductVariant
from django.views import View
from django.http import JsonResponse


# Create your views here.

# adding items to basket
class BasketAddView(View):
    def post(self, request, *args, **kwargs):
        form = BasketAddForm(request.POST)

        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "error": "login_required"}, status=403)

        if form.is_valid():
            variant_id = form.cleaned_data['variant_id']
            quantity = form.cleaned_data['quantity']

            variant = get_object_or_404(ProductVariant, id=variant_id)

            # Get or create basket
            basket, _ = Basket.objects.get_or_create(user=request.user)

            # Add or update item
            item, created = BasketItem.objects.get_or_create(
                basket=basket,
                variant=variant,
                defaults={"quantity": quantity},
            )

            if not created:
                item.quantity += quantity
                item.save()

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

        return JsonResponse({"success": False}, status=400)
        #     messages.success(request, f"Added {quantity} X {variant.product.name} ({variant.name}) to your basket!")
        
        # else:

        #     messages.error(request, "Failed to add item to basket..")

        # # return redirect("basket:basket")
        # return redirect(request.META.get('HTTP_REFERER', '/'))


#removing item from basket

class BasketRemoveView(LoginRequiredMixin, View):

    def post(self, request, variant_id, *args, **kwargs):
        basket = get_object_or_404(Basket, user=request.user)
        item = get_object_or_404(BasketItem, basket=basket, variant_id=variant_id)
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
            item.quantity += 1
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