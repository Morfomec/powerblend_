from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from user_profile.models import Address
from decimal import Decimal 
from django.db import transaction
from django.contrib.auth.decorators import login_required
from orders.models import Order
from basket.models import Basket
from orders.utils import decrement_stock
from products.models import ProductVariant
from django.core.exceptions import ValidationError

import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest

# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))


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
        print('getting post')
        try: 
            payment_method = request.POST.get("payment_method")

        except Exception as e:
            print(str(e))

            messages.error(request, f"Payment method error is {str(e)}!!")

        shipping_address = (
            f"{default_address.full_name}<br>"
            f"{default_address.address}<br>"
            f"{default_address.city}, {default_address.state}<br>"
            f"{default_address.postal_code}, {default_address.country}"
        )

        #1. create order
        order = Order.objects.create(user=request.user, shipping_address=shipping_address, subtotal=subtotal, total=total, payment_method=payment_method, status='pending')
        print('order created')
        with transaction.atomic():
            #2. creare orderitems from basket items
            for item in basket_items:

                variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                print("Variant ID:", variant.id)
                print("Current stock in DB:", variant.stock)
                variant.refresh_from_db()
                if variant.stock < item.quantity:
                    messages.error(request, f"Not enough stock for {variant.product.name}. Only {variant.stock} left.")
                    transaction.set_rollback(True)  # rollback the current transaction
                    return redirect('basket_view')

                

                order.items.create(variant=item.variant, quantity=item.quantity, price=item.subtotal)
                
                decrement_stock(item.variant, item.quantity)
                
        

            #3. clear basket after order creation
            # basket_items.all().delete()  
            
        try:
            print("Payment method received:", payment_method)
            if payment_method == 'cod':
                return redirect('order_success', order_id=order.id)
            elif payment_method == 'wallet':
                return redirect('order_success', order_id=order.id)
                
            elif payment_method == 'razorpay':
                amount = int(total * 100)
                currency = 'INR'
                print(f"Creating Razorpay order: amount={amount}, currency='{currency}'")
                razorpay_order = razorpay_client.order.create({
                    "amount": amount,
                    "currency": currency,
                    "payment_capture": "1"  # auto capture
                })
                print('razorpay')
                # print('1')
                
                # order id of newly created order.
                razorpay_order_id = razorpay_order['id']
                order.razorpay_order_id = razorpay_order_id  # Save this line
                order.save()
                callback_url = 'paymenthandler/'

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

                    # Razorpay integration data
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_merchant_key': settings.RAZOR_KEY_ID,
                    'razorpay_amount': amount,
                    'currency': currency,
                    'callback_url': callback_url,

                }
                print('last')
                return render(request, 'checkout.html', context)
            
        except Exception as e:
                print(str(e))
                return render(request, 'checkout.html', context)




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



# @csrf_exempt
# def paymenthandler(request):
#     """
#     Handles Razorpay payment confirmation and verifies the payment signature.
#     """
#     if request.method == "POST":
#         try:
#             # Get payment details from POST
#             payment_id = request.POST.get('razorpay_payment_id', '')
#             razorpay_order_id = request.POST.get('razorpay_order_id', '')
#             signature = request.POST.get('razorpay_signature', '')

#             params_dict = {
#                 'razorpay_order_id': razorpay_order_id,
#                 'razorpay_payment_id': payment_id,
#                 'razorpay_signature': signature
#             }

#             # Verify the payment signature
#             result = razorpay_client.utility.verify_payment_signature(params_dict)
            
#             if result is None:
#                 # ❌ Signature verification failed
#                 return render(request, 'paymentfail.html')

#             # ✅ Signature verified successfully
#             # Find your order from DB using Razorpay order ID
#             from orders.models import Order  # import here to avoid circular import
#             order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()

#             # You may have stored Razorpay order ID in your Order model
#             # If not, we’ll add that next.

#             if not order:
#                 # fallback if not stored; handle gracefully
#                 return render(request, 'paymentfail.html')

#             amount = int(order.total * 100)  # amount in paise

#             try:
#                 # Capture the payment
#                 razorpay_client.payment.capture(payment_id, amount)

#                 # Update order status
#                 order.payment_status = 'paid'
#                 order.razorpay_payment_id = payment_id
#                 order.save()

#                 return render(request, 'order_success.html', {'order': order})

#             except Exception as e:
#                 print("Payment capture error:", e)
#                 return render(request, 'paymentfail.html')

#         except Exception as e:
#             print("Payment handler exception:", e)
#             return HttpResponseBadRequest("Invalid Request Data")

#     else:
#         return HttpResponseBadRequest("Invalid Method")



@csrf_exempt
def paymenthandler(request):

    # only accept POST request.
    if request.method == "POST":
        try:
          
            # get the required parameters from post request.
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            # verify the payment signature.
            result = razorpay_client.utility.verify_payment_signature(
                params_dict)
            if result is not None:
                amount = 20000  # Rs. 200
                try:

                    # capture the payemt
                    razorpay_client.payment.capture(payment_id, amount)

                    # render success page on successful caputre of payment
                    return render(request, 'paymentsuccess.html')
                except:

                    # if there is an error while capturing payment.
                    return render(request, 'paymentfail.html')
            else:

                # if signature verification fails.
                return render(request, 'paymentfail.html')
        except:

            # if we don't find the required parameters in POST data
            return HttpResponseBadRequest()
    else:
       # if other than POST request is made.
        return HttpResponseBadRequest()