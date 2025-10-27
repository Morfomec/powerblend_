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
from admin_app.forms import ApplyCouponForm
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
import razorpay

# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))



@login_required
def checkout_view(request):
    """
    Checkout page with default address, basket, coupon, wallet, COD, Razorpay handling.
    """
    
    # --- Default address ---
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    if not default_address:
        messages.error(request, "Please choose a default address before checkout.")
        return redirect('checkout')

    # --- Basket ---
    basket = getattr(request.user, 'basket', None)
    if not basket or not basket.items.exists():
        messages.error(request, "Your basket is empty!")
        return redirect('basket_view')

    basket_items = basket.items.select_related('variant', 'variant__product').all()
    subtotal = basket.total_price
    total_items = basket.total_items

    # --- Tax, shipping ---
    shipping = Decimal('0')
    taxes = subtotal * Decimal('0')

    # --- Coupon form & available coupons ---
    coupon_form = ApplyCouponForm()
    today = timezone.now().date()
    available_coupons = Coupon.objects.filter(
        is_active=True, valid_from__lte=today, valid_to__gte=today
    ).order_by('-valid_to')

    #Handle removing coupon 

    if request.method == 'POST' and 'remove_coupon' in request.POST:
        request.session.pop('applied_coupon', None)
        messages.info(request, "Coupon removed successfully", extra_tags='remove_coupon')
        return redirect('checkout')

    # --- Handle applying coupon ---
    applied_coupon = None
    discount_amount = Decimal('0')

    if request.method == 'POST' and 'apply_coupon' in request.POST:
        coupon_form = ApplyCouponForm(request.POST)
        if coupon_form.is_valid():
            code = coupon_form.cleaned_data['code'].strip().upper()
            try:
                coupon = Coupon.objects.get(code__iexact=code, is_active=True)
                if coupon.is_valid() and subtotal >= coupon.minimum_amount:
                    request.session['applied_coupon'] = coupon.code
                    discount_amount = coupon.discount_amount
                    applied_coupon = coupon
                    messages.success(
                        request,
                        f"Coupon {coupon.code} applied successfully!",
                        extra_tags='coupon_applied_successfull'
                    )
                else:
                    messages.error(
                        request,
                        "Coupon is invalid or order does not meet minimum amount.",
                        extra_tags='coupon_applied_not_minimum_meet'
                    )
                    request.session.pop('applied_coupon', None)
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid coupon code.", extra_tags='invalid_coupon')
                request.session.pop('applied_coupon', None)
        return redirect('checkout')

    # --- Load coupon from session if exists ---
    coupon_code = request.session.get('applied_coupon')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
            if coupon.is_valid() and subtotal >= coupon.minimum_amount:
                discount_amount = coupon.discount_amount
                applied_coupon = coupon
            else:
                request.session.pop('applied_coupon', None)
        except Coupon.DoesNotExist:
            request.session.pop('applied_coupon', None)

    # --- Total calculation ---
    total = subtotal + taxes + shipping - discount_amount
    total = max(total, 0)

    # --- Handle payment submission ---
    order = None
    if request.method == 'POST' and 'payment_method' in request.POST:
        payment_method = request.POST.get('payment_method')
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        shipping_address = (
            f"{default_address.full_name}\n"
            f"{default_address.address}\n"
            f"{default_address.city}, {default_address.state}\n"
            f"{default_address.postal_code}, {default_address.country}"
        )

        # --- Create order ---
        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address,
            subtotal=subtotal,
            total=total,
            payment_method=payment_method,
            discount_amount=discount_amount,
            status='pending'
        )

        # --- Save order items and decrement stock ---
        with transaction.atomic():
            for item in basket_items:
                variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                if variant.stock < item.quantity:
                    messages.error(request, f"Not enough stock for {variant.product.name}. Only {variant.stock} left.")
                    transaction.set_rollback(True)
                    return redirect('basket_view')

                order.items.create(
                    variant=item.variant,
                    quantity=item.quantity,
                    price=item.subtotal
                )
                decrement_stock(item.variant, item.quantity)

        # --- Payment handling ---
        try:
            if payment_method == 'cod':
                return redirect('order_success', order_id=order.id)

            elif payment_method == 'wallet':
                if wallet.balance < total:
                    messages.error(request, "Insufficient wallet balance!", extra_tags='checkout-wallet_insufficient')
                    return redirect('checkout')

                with transaction.atomic():
                    wallet.debit(total)
                    order.status = 'confirmed'
                    order.payment_status = 'paid'
                    order.save()
                return redirect('order_success', order_id=order.id)

            elif payment_method == 'razorpay':
                amount = int(total * 100)
                currency = 'INR'
                razorpay_order = razorpay_client.order.create({
                    "amount": amount,
                    "currency": currency,
                    "payment_capture": "1"
                })
                razorpay_order_id = razorpay_order['id']
                order.status = 'confirmed'
                order.payment_status = 'paid'
                order.razorpay_order_id = razorpay_order_id
                order.save()
                callback_url = 'paymenthandler/'

                context = {
                    'default_address': default_address,
                    'basket_items': basket_items,
                    'subtotal': subtotal,
                    'total_items': total_items,
                    'shipping': shipping,
                    'taxes': taxes,
                    'discount': discount_amount,
                    'total': total,
                    'order': order,
                    'wallet_balance': wallet.balance,
                    'available_coupons': available_coupons,
                    'applied_coupon': applied_coupon,
                    'coupon_form': coupon_form,

                    # Razorpay integration
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_merchant_key': settings.RAZOR_KEY_ID,
                    'razorpay_amount': amount,
                    'currency': currency,
                    'callback_url': callback_url,
                }
                return render(request, 'checkout.html', context)

        except Exception as e:
            messages.error(request, f"Payment processing error: {str(e)}")
            return redirect('checkout')

    # --- Default context for rendering page ---
    context = {
        'default_address': default_address,
        'basket_items': basket_items,
        'subtotal': subtotal,
        'total_items': total_items,
        'shipping': shipping,
        'taxes': taxes,
        'discount': discount_amount,
        'total': total,
        'order': order,
        'available_coupons': available_coupons,
        'applied_coupon': applied_coupon,
        'coupon_form': coupon_form,
    }

    return render(request, 'checkout.html', context)



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