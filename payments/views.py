from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from user_profile.models import Address
from decimal import Decimal 



# Create your views here.

def checkout_view(request):
    """
    Default address would be shown on checkout page and basket items.
    """

    default_address = Address.objects.filter(user=request.user, is_default=True).first()

    # to get basket
    basket = getattr(request.user, 'basket', None)

    if basket:
        basket_items = basket.items.select_related('variant', 'variant__product').all()
        subtotal = basket.total_price * Decimal('0.95')
        total_items = basket.total_items
    else:
        basket_items = []
        subtotal = 0
        total_items = 0

    #tax and shipping calculation

    shipping = Decimal('0')
    discount = Decimal('0')
    taxes = subtotal * Decimal('0.12')
    total = subtotal + taxes + shipping - discount
    

    context = {
        'default_address' : default_address,
        'basket_items' : basket_items,
        'subtotal': subtotal,
        'total_items':total_items,
        'shipping' : shipping,
        'taxes' : taxes,
        'discount' : discount,
        'total' : total,
    }


    if default_address:
           print("Default:", default_address.is_default)

    
    return render(request, 'checkout.html', context)

