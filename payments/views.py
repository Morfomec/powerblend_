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
from wallet.models import Wallet
from admin_app.models import Coupon
from django.utils import timezone
from coupons.forms import ApplyCouponForm
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
import razorpay

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
    discount_amount = Decimal('0')
    taxes = subtotal * Decimal('0.12')
    total = subtotal + taxes + shipping - discount_amount

    applied_coupon = None
    discount_amount = Decimal(0)
    coupon_form = ApplyCouponForm()

    today = timezone.now().date()
    available_coupons = Coupon.objects.filter( is_active=True, valid_from__lte=today,valid_to__gte=today).order_by('-valid_to')


    user = request.user
    basket = user.basket
    basket_total = basket.total_price


    # handling coupon forms
    if request.method == 'POST' and 'apply_coupon' in request.POST:
        coupon_form = ApplyCouponForm(request.POST)
        if coupon_form.is_valid():
            code = coupon_form.cleaned_data['code'].strip().upper()
            today = timezone.now().date()
            try:
                coupon = Coupon.objects.get(code__iexact=code, is_active=True)
                if coupon.is_valid() and basket_total >= coupon.minimum_amount:
                    discount_amount = coupon.discount_amount
                    applied_coupon = coupon
                    messages.success(request, f"Coupon {coupon.code} applied successfully!")
                else:
                    messages.error(request, "Coupon is invalid or order not meet minimum amount.")
            except coupon.DoesNotExist:
                messages.error(request, "Invalid coupon code.")
    else:
        coupon_form = ApplyCouponForm()
        coupon_discount = request.session.get('applied_coupon')
        if coupon_discount:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_discount, is_active=True)
                if coupon.is_valid() and basket_total >= coupon.minimum_amount:
                    discount_amount = coupon.discount_amount
                    applied_coupon = coupon
            except Coupon.DoesNotExist:
                pass


    total = subtotal + taxes + shipping - discount_amount
    total = max(total, 0)

    # handle form submission / payment

    if request.method == 'POST':
        print('getting post')
        try: 
            payment_method = request.POST.get("payment_method")
            wallet,_ = Wallet.objects.get_or_create(user=request.user)

        except Exception as e:
            print(str(e))

            messages.error(request, f"Payment method error is {str(e)}!!")

        shipping_address = (
            f"{default_address.full_name}\n\n"
            f"{default_address.address}\n\n"
            f"{default_address.city}, {default_address.state}\n"
            f"{default_address.postal_code}, {default_address.country}"
        )

        #1. create order
        order = Order.objects.create(user=request.user, shipping_address=shipping_address, subtotal=subtotal, total=total, payment_method=payment_method,discount_amount=discount_amount, coupon=applied_coupon, paid_amout=total, status='pending')
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
        'available_coupons' : available_coupons,
        'applied_coupon' : applied_coupon,
        'coupon_form':coupon_form,

    }


        # 3. clear basket after order creation
        # basket_items.all().delete()
        

    if request.method == 'POST':

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
           
        try:
            print("Payment method received:", payment_method)
            if payment_method == 'cod':
                return redirect('order_success', order_id=order.id)
            elif payment_method == 'wallet':

                if wallet.balance < total:
                    messages.error(request, "Insufficient wallet balance!")
                    return redirect('checkout')

                with transaction.atomic():
                    wallet.debit(total)
                    order.status='confirmed'
                    order.payment_status = 'paid'
                    order.save()
                    # order = Order.objects.create(user=request.user, total=total, payment_method='wallet', status='confirmed')
                # messages.success(request, f"₹{total:.2f} paid from wallet successfully!")
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
                order.status = 'confirmed'
                order.payment_status = 'paid'
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
                    'wallet_balance' : wallet.balance,
                    'available_coupons' : available_coupons,
                    'applied_coupon' : coupon,
                    'coupon_form' : coupon_form,

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




    # context = {
    #     'default_address' : default_address,
    #     'basket_items' : basket_items,
    #     'subtotal': subtotal,
    #     'total_items':total_items,
    #     'shipping' : shipping,
    #     'taxes' : taxes,
    #     'discount' : discount,
    #     'total' : total,
    #     'order' : order,

    # }
    
    # return render(request, 'checkout.html', context)


# @login_required
# def checkout_view(request):
#     # --- Get default address ---
#     default_address = Address.objects.filter(user=request.user, is_default=True).first()
#     if not default_address:
#         messages.error(request, "Please choose a default address before checkout.")
#         return redirect('checkout')

#     # --- Get user's basket ---
#     basket = getattr(request.user, 'basket', None)
#     if not basket or not basket.items.exists():
#         messages.error(request, "Your basket is empty!")
#         return redirect('basket_view')

#     basket_items = basket.items.select_related('variant', 'variant__product').all()
#     subtotal = basket.total_price
#     total_items = basket.total_items

#     shipping = Decimal('0')
#     taxes = subtotal * Decimal('0.12')

#     # --- Coupon initialization ---
#     applied_coupon = None
#     discount_amount = Decimal(0)
#     coupon_form = ApplyCouponForm()
#     today = timezone.now().date()
#     available_coupons = Coupon.objects.filter(
#         is_active=True, valid_from__lte=today, valid_to__gte=today
#     ).order_by('-valid_to')

#     # --- Handle POST requests ---
#     if request.method == 'POST':
#         # Determine which form was submitted
#         if 'apply_coupon' in request.POST:
#             coupon_form = ApplyCouponForm(request.POST)
#             if coupon_form.is_valid():
#                 code = coupon_form.cleaned_data['code'].strip().upper()
#                 try:
#                     coupon = Coupon.objects.get(code__iexact=code, is_active=True)
#                     if coupon.is_valid() and subtotal >= coupon.minimum_amount:
#                         discount_amount = coupon.discount_amount
#                         applied_coupon = coupon
#                         messages.success(request, f"Coupon {coupon.code} applied successfully!")
#                     else:
#                         messages.error(request, "Coupon is invalid or order does not meet minimum amount.")
#                 except Coupon.DoesNotExist:
#                     messages.error(request, "Invalid coupon code.")
#         elif 'place_order' in request.POST:
#             # --- Payment and order creation ---
#             payment_method = request.POST.get("payment_method")
#             wallet, _ = Wallet.objects.get_or_create(user=request.user)

#             total = subtotal + taxes + shipping - discount_amount
#             total = max(total, 0)

#             shipping_address = (
#                 f"{default_address.full_name}\n"
#                 f"{default_address.address}\n"
#                 f"{default_address.city}, {default_address.state}\n"
#                 f"{default_address.postal_code}, {default_address.country}"
#             )

#             with transaction.atomic():
#                 # Create the order
#                 order = Order.objects.create(
#                     user=request.user,
#                     shipping_address=shipping_address,
#                     subtotal=subtotal,
#                     total=total,
#                     payment_method=payment_method,
#                     discount_amount=discount_amount,
#                     coupon=applied_coupon,
#                     paid_amount=total,
#                     status='pending'
#                 )

#                 # Add order items and decrement stock
#                 for item in basket_items:
#                     variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
#                     variant.refresh_from_db()
#                     if variant.stock < item.quantity:
#                         messages.error(request, f"Not enough stock for {variant.product.name}. Only {variant.stock} left.")
#                         transaction.set_rollback(True)
#                         return redirect('basket_view')
#                     order.items.create(
#                         variant=item.variant,
#                         quantity=item.quantity,
#                         price=item.subtotal
#                     )
#                     decrement_stock(item.variant, item.quantity)

#                 # Handle payment methods
#                 if payment_method == 'cod':
#                     order.status = 'confirmed'
#                     order.payment_status = 'pending'
#                     order.save()
#                     basket.items.all().delete()
#                     return redirect('order_success', order_id=order.id)
                
#                 elif payment_method == 'wallet':
#                     if wallet.balance < total:
#                         messages.error(request, "Insufficient wallet balance!")
#                         return redirect('checkout')
#                     wallet.debit(total)
#                     order.status = 'confirmed'
#                     order.payment_status = 'paid'
#                     order.save()
#                     basket.items.all().delete()
#                     return redirect('order_success', order_id=order.id)
                
#                 elif payment_method == 'razorpay':
#                     from django.conf import settings
#                     import razorpay
#                     client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
#                     amount = int(total * 100)
#                     razorpay_order = client.order.create({
#                         "amount": amount,
#                         "currency": "INR",
#                         "payment_capture": "1"
#                     })
#                     order.status = 'confirmed'
#                     order.payment_status = 'paid'
#                     order.razorpay_order_id = razorpay_order['id']
#                     order.save()
#                     basket.items.all().delete()
#                     context = {
#                         'default_address': default_address,
#                         'basket_items': basket_items,
#                         'subtotal': subtotal,
#                         'total_items': total_items,
#                         'shipping': shipping,
#                         'taxes': taxes,
#                         'discount': discount_amount,
#                         'total': total,
#                         'order': order,
#                         'wallet_balance': wallet.balance,
#                         'available_coupons': available_coupons,
#                         'applied_coupon': applied_coupon,
#                         'coupon_form': coupon_form,
#                         'razorpay_order_id': razorpay_order['id'],
#                         'razorpay_merchant_key': settings.RAZOR_KEY_ID,
#                         'razorpay_amount': amount,
#                         'currency': 'INR',
#                         'callback_url': 'paymenthandler/'
#                     }
#                     return render(request, 'checkout.html', context)

    # --- Calculate total for display ---
    total = subtotal + taxes + shipping - discount_amount
    total = max(total, 0)

    context = {
        'default_address': default_address,
        'basket_items': basket_items,
        'subtotal': subtotal,
        'total_items': total_items,
        'shipping': shipping,
        'taxes': taxes,
        'discount': discount_amount,
        'total': total,
        'order': None,
        'available_coupons': available_coupons,
        'applied_coupon': applied_coupon,
        'coupon_form': coupon_form,
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
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')

            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            # Verify signature
            try:
                razorpay_client.utility.verify_payment_signature(params_dict)
            except:
                return render(request, 'paymentfail.html')

            # Update order
            order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if not order:
                return render(request, 'paymentfail.html')

            order.payment_status = 'paid'
            order.razorpay_payment_id = payment_id
            order.save()

            return redirect('order_success', order_id=order.id)

        except Exception as e:
            print("Payment handler error:", e)
            return HttpResponseBadRequest("Invalid request")
    return HttpResponseBadRequest("Invalid method")