from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Basket, BasketItem
from .forms import BasketAddForm
from products.models import ProductVariant
from django.views import View

# Create your views here.

# adding items to basket
class BasketAddView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        
        form = BasketAddForm(request.POST)
        if form.is_valid():
            variant_id = form.cleaned_data['variant_id']
            quantity = form.cleaned_data['quantity']

            variant = get_object_or_404(ProductVariant, id=variant_id)
            
            #to get or create basket
            basket, _ = Basket.objects.get_object_or_404(user=request.user)


            #to add or update item
            item, created = BasketItem.objects.get_object_or_404(basket = basket, variant=variant, defaults={'quantity':quantity})

            if not created:
                item.quantity += quantity
                item.save()

        return redirect("basket:basket")


#removing item from basket

class BasketRemoveView(LoginRequiredMixin, View):

    def post(self, request, variant_id, *args, **kwargs):
        basket = get_object_or_404(Basket, user=request.user)
        item = get_object_or_404(BasketItem, basket=basket, variant_id=variant_id)
        item.delete()
        return redirect("basket:basket")


#Basket datails view all items
class BasketDetailView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        basket, _ = Basket.object.get_object_or_404(user=request.user)
        items = basket.items.select_related('variant', 'variant__product')
        total_price = sum(item.variant.price * item.quantity for item in items)
        context = {
            "basket": basket,
            "items" : items,
            "total_price" : total_price,
        }

        return render(request, 'basket.html', context)