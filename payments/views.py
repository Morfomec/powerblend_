from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from user_profile.models import Address
from decimal import Decimal 
from django.db import transaction
from django.contrib.auth.decorators import login_required
from orders.models import Order
from basket.models import Basket
from orders.utils import decrement_stock



# Create your views here.
@login_required
def checkout_view(request):
    """
    Default address would be shown on checkout page and basket items.
    """
    
    default_address = Address.objects.filter(user=request.user, is_default=True).first()

    if not default_address:
        messages.error(request, "Please choose a default address before checkout.")
        return redirect('checkout')

    order = None

    # to get basket
    basket = Basket.objects.filter(user=request.user).first()

    if not basket or not basket.items.exists():
        messages.error(request, "Your basket is empty!")
        return redirect('basket_view')

    #basket details

    basket_items = basket.items.select_related('variant', 'variant__product').all()
    subtotal = basket.total_price
    total_items = basket.total_items

    #tax and shipping calculation

    shipping = Decimal('0')
    discount = Decimal('0')
    taxes = subtotal * Decimal('0.12')
    total = subtotal + taxes + shipping - discount

    # handle form submission / payment

    if request.method == 'POST':
        try: 
            payment_method = request.POST.get("payment_method")

        except Exception as e:
            messages.error(request, f"Payment method error is {str(e)}!!")

        # shipping_address = (
        #     f"{default_address.full_name} <br>"
        #     f"{default_address.address}<br>"
        #     f"{default_address.city}, {default_address.state}<br>"
        #     f"{default_address.postal_code}, {default_address.country}"
        # )

        shipping_address = (
            f"{default_address.full_name}<br>"
            f"{default_address.address}<br>"
            f"{default_address.city}, {default_address.state}<br>"
            f"{default_address.postal_code}, {default_address.country}"
        )

        #1. create order
        order = Order.objects.create(user=request.user, shipping_address=shipping_address, subtotal=subtotal, total=total, payment_method=payment_method, status='pending')

        with transaction.atomic():
            #2. creare orderitems from basket items
            for item in basket_items:
                order.items.create(variant=item.variant, quantity=item.quantity, price=item.subtotal)
                
                decrement_stock(item.variant, item.quantity)
        

            #3. clear basket after order creation
            # basket_items.all().delete()  

        if payment_method == 'cod':
            return redirect('order_success', order_id=order.id)
        elif payment_method == 'razorpay':
            return redirect('order_success', order_id=order.id)
        elif payment_method == 'wallet':
            return redirect('order_success', order_id=order.id)



    context = {
        'default_address' : default_address,
        'basket_items' : basket_items,
        'subtotal': subtotal,
        'total_items':total_items,
        'shipping' : shipping,
        'taxes' : taxes,
        'discount' : discount,
        'total' : total,
        'order' : order,
    }
    
    return render(request, 'checkout.html', context)



