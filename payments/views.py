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
from admin_app.models import Coupon, UserCoupon
from django.utils import timezone
from admin_app.forms import ApplyCouponForm
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
from user_profile.forms import AddressForm
import razorpay



# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))


def create_order_with_coupon(user, payment_method, subtotal, total, discount_amount,address, coupon=None, status='pending', payment_status='pending'):
    """
    create an order while preserving coupon and originla price info.
    """

    order = Order.objects.create(
        user=user,
        shipping_address=address,
        subtotal=subtotal,
        total=total,
        original_total=subtotal,
        amount_paid=total,  
        payment_method=payment_method,
        discount_amount=discount_amount,
        status=status,
        payment_status=payment_status,
    )

    if coupon:
        order.coupon_code = coupon.code
        order.coupon_discount = coupon.discount_amount
        order.coupon_min_amount = coupon.minimum_amount
        order.save(update_fields=['coupon_code', 'coupon_discount', 'coupon_min_amount'])

    return order

@login_required
def checkout_view(request):
    """
    Checkout page with default address, basket, coupon, wallet, COD, Razorpay handling.
    """
    



    #address handling from the checkout page itself
    addresses = Address.objects.filter(user=request.user).order_by('-is_default')


    #flag to re open modal if there is vlaidation error

    reopen_modal = False


    if request.method == 'POST' and 'address_create' in request.POST:
        address_form = AddressForm(request.POST)
        if address_form.is_valid():
            new_address = address_form.save(commit=False)
            new_address.user = request.user
            new_address.save()
            messages.success(request, "New address added successfully!", extra_tags='address_added')
            return redirect('checkout')
        else:
            # Form has errors - they'll be displayed in the modal
            messages.error(request, "Please correct the errors in the address form.")
            reopen_modal = True
    else:
        address_form = AddressForm()


    # --- Default address ---
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    if not default_address and addresses.exists():
        default_address =addresses.first()
    elif not default_address:
        default_address = None
        # messages.error(request, "Please choose a default address before checkout.")
        # return redirect('checkout')



    # --- Basket ---
    basket = getattr(request.user, 'basket', None)
    if not basket or not basket.items.exists():
        messages.error(request, "Your basket is empty!")
        return redirect('basket_view')

    basket_items = basket.items.select_related('variant', 'variant__product').all()
    subtotal = basket.total_price
    total_items = basket.total_items

    # --- Tax, shipping ---
    shipping = Decimal('0.00')
    taxes = subtotal * Decimal('0.00')

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

                if UserCoupon.objects.filter(user=request.user, coupon=coupon).exists():
                    messages.error(request, "You have already used this coupon.", extra_tags="coupn_used")
                    return redirect('checkout')

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

    # -----------------------
    # GET: render checkout page (no `order` in context)
    # -----------------------
    if request.method == 'GET':
        context = {
            'default_address': default_address,
            'addresses': addresses,
            'address_form': address_form,
            'reopen_modal': reopen_modal,
            'basket_items': basket_items,
            'subtotal': subtotal,
            'total_items': total_items,
            'shipping': shipping,
            'taxes': taxes,
            'discount': discount_amount,
            'total': total,
            'available_coupons': available_coupons,
            'applied_coupon': applied_coupon,
            'coupon_form': coupon_form,
            'wallet_balance': getattr(Wallet.objects.filter(user=request.user).first(), 'balance', Decimal('0')),
        }
        return render(request, 'checkout.html', context)

    


    # --- Handle payment submission ---
    order = None

    # ensure payment_method posted
    if not (request.method == 'POST' and 'payment_method' in request.POST):
        print(f"✅ Payment method POST received: {request.POST.get('payment_method')}")

        messages.error(request, "No payment method selected.")
        return redirect('checkout')

    payment_method = request.POST.get('payment_method')
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    wallet.balance = wallet.balance

    shipping_address = (
        f"{default_address.full_name}\n"
        f"{default_address.address}\n"
        f"{default_address.city}, {default_address.state}\n"
        f"{default_address.postal_code}, {default_address.country}"
    )

    if payment_method == 'cod' and total > 1000:
        messages.warning(request, "Cash on delivery cannot be more than 1000 rupees!!", extra_tags="cod_1000")
        return redirect('checkout')
    
    # Wallet balance check
    if payment_method == 'wallet' and wallet.balance < total:
        messages.error(request, "Insufficient wallet balance!", extra_tags='checkout-wallet_insufficient')
        return redirect('checkout')

        # elif payment_method == 'cod':

        #     # basket.items.all().delete()
        #     # basket.is_active = False
        #     # basket.save()

        #     return redirect('order_success', order_id=order.id)

    # Stock availability check for all items (no decrement here)
    for item in basket_items:
        variant = ProductVariant.objects.select_related('product').get(id=item.variant.id)
        if variant.stock < item.quantity:
            messages.error(request, f"Not enough stock for {variant.product.name}. Only {variant.stock} left.")
            return redirect('basket_view')

    
    if payment_method == 'cod':
        try:
            with transaction.atomic():
        
                # --- Create order ---
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=shipping_address,
                    subtotal=subtotal,
                    total=total,
                    original_total=subtotal,
                    payment_method='cod',
                    discount_amount=discount_amount,
                    payment_status='pending',
                    status='pending',
                )
                
                # order = create_order_with_coupon(
                #     user=request.user,
                #     payment_method='cod',
                #     subtotal=subtotal,
                #     total=total,
                #     discount_amount=discount_amount,
                #     address=shipping_address,
                #     coupon=applied_coupon,
                # )

                if applied_coupon:
                    UserCoupon.objects.get_or_create(user=request.user, coupon=applied_coupon)
                    # clearing coupon from session once used
                    request.session.pop("applied_coupon", None)
                    request.session.modified = True

                # create order items and decrement stock (lock rows)
                for item in basket_items:
                    variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                    if variant.stock < item.quantity:
                        # Shouldn't happen because we checked earlier, but guard anyway
                        messages.error(request, f"Not enough stock for {variant.product.name}. Only {variant.stock} left.")
                        transaction.set_rollback(True)
                        return redirect('basket_view')

                    order.items.create(
                        variant=item.variant,
                        quantity=item.quantity,
                        price=item.subtotal
                    )
                    decrement_stock(item.variant, item.quantity)

                # clear basket after successful order creation
                # basket.items.all().delete()
                # basket.is_active = False
                # basket.save()

            return redirect('order_success', order_id=order.id)

        except Exception as e:
            messages.error(request, f"Error creating COD order: {str(e)}")
            return redirect('checkout')

    # ------ WALLET: debit first, then create order & decrement stock ------
    if payment_method == 'wallet':
        try:
            with transaction.atomic():
                print("💳 Wallet payment initiated...")
                # Debit wallet first (this is your wallet.debit method)
                wallet.debit(total)  # assuming this saves and raises on failure

                # Create order as paid
                # order = Order.objects.create(
                #     user=request.user,
                #     shipping_address=shipping_address,
                #     subtotal=subtotal,
                #     total=total,
                #     original_total=subtotal,
                #     payment_method='wallet',
                #     discount_amount=discount_amount,
                #     status='confirmed',
                #     payment_status='paid',
                #     amount_paid=total,
                # )

                order = create_order_with_coupon(
                    user=request.user,
                    payment_method='wallet',
                    subtotal=subtotal,
                    total=total,
                    discount_amount=discount_amount,
                    address=shipping_address,
                    coupon=applied_coupon,
                    status='confirmed',
                    payment_status='paid',
                )

                if applied_coupon:
                    UserCoupon.objects.get_or_create(user=request.user, coupon=applied_coupon)
                    # now clearing coupon from session once used 
                    request.session.pop('applied_coupon', None)
                    request.session.modified=True

                print(f"✅ Order created with ID: {order.id}")

                # create items and decrement stock with select_for_update
                for item in basket_items:
                    variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                    if variant.stock < item.quantity:
                        # rollback: impossible if earlier stock check passed, but just in case
                        messages.error(request, f"Not enough stock for {variant.product.name}. Only {variant.stock} left.")
                        transaction.set_rollback(True)
                        # optionally refund wallet here (if debit succeeded) - your wallet.debit should be atomic / reversible
                        return redirect('basket_view')

                    order.items.create(
                        variant=item.variant,
                        quantity=item.quantity,
                        price=item.subtotal
                    )
                    decrement_stock(variant, item.quantity)

                # mark order items confirmed
                order.items.update(status='confirmed')

                # clear basket
                # basket.items.all().delete()
                # basket.is_active = False
                # basket.save()

            return redirect('order_success', order_id=order.id)

        except Exception as e:
            print("❌ Wallet payment failed:", str(e))
            messages.error(request, f"Wallet payment failed: {str(e)}")
            return redirect('checkout')

    # ------ RAZORPAY: create razorpay order (remote) & store checkout snapshot in session ------
    if payment_method == 'razorpay':
        try:
            # create razorpay order (amount in paise)
            amount = int(total * 100)
            currency = 'INR'
            razorpay_order = razorpay_client.order.create({
                "amount": amount,
                "currency": currency,
                "payment_capture": "1"
            })
            razorpay_order_id = razorpay_order['id']

            # Save minimal checkout snapshot in session so paymenthandler can reconstruct
            # converting Decimals to strings for JSON-serializable session
            items_snapshot = []
            for item in basket_items:
                items_snapshot.append({
                    'variant_id': item.variant.id,
                    'quantity': item.quantity,
                    'price': str(item.subtotal),
                })

            request.session['razorpay_checkout'] = {
                'razorpay_order_id': razorpay_order_id,
                'items': items_snapshot,
                'subtotal': str(subtotal),
                'discount_amount': str(discount_amount),
                'total': str(total),
                'shipping_address': shipping_address,
            }
            # ensure session saved
            request.session.modified = True

            # Render checkout again (or a dedicated razorpay page) with keys required by frontend
            context = {
                'default_address': default_address,
                'basket_items': basket_items,
                'subtotal': subtotal,
                'total_items': total_items,
                'shipping': shipping,
                'taxes': taxes,
                'discount': discount_amount,
                'total': total,
                'wallet_balance': wallet.balance,
                'available_coupons': available_coupons,
                'applied_coupon': applied_coupon,
                'coupon_form': coupon_form,
                # Razorpay data for frontend
                'razorpay_order_id': razorpay_order_id,
                'razorpay_merchant_key': settings.RAZOR_KEY_ID,
                'razorpay_amount': amount,
                'currency': currency,
                'callback_url': '/payment/paymenthandler/',  
            }
            return render(request, 'checkout.html', context)

        except Exception as e:
            messages.error(request, f"Razorpay order creation failed: {str(e)}")
            return redirect('checkout')

    # fallback
    messages.error(request, "Invalid payment method selected.")
    return redirect('checkout')



@csrf_exempt
@login_required
def paymenthandler(request):
    """
    Razorpay callback — finalizes the order after successful payment.
    This endpoint is hit via POST from Razorpay JS after the user pays.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method")

    try:
        # --- Step 1: Extract Razorpay data ---
        payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        # Basic validation
        if not (payment_id and razorpay_order_id and signature):
            messages.error(request, "Missing payment details from Razorpay.")
            return redirect('checkout')

        # --- Step 2: Verify signature authenticity ---
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            messages.error(request, "Payment verification failed! Please contact support.")
            return render(request, 'paymentfail.html')

        # --- Step 3: Retrieve session snapshot ---
        snapshot = request.session.get('razorpay_checkout')
        if not snapshot or snapshot.get('razorpay_order_id') != razorpay_order_id:
            messages.error(request, "Session expired or invalid order data.")
            return redirect('checkout')

        subtotal = Decimal(snapshot['subtotal'])
        discount_amount = Decimal(snapshot['discount_amount'])
        total = Decimal(snapshot['total'])
        shipping_address = snapshot.get('shipping_address', '')
        items_snapshot = snapshot.get('items', [])

        # --- Step 4: Validate and Create Final Order ---
        with transaction.atomic():
            # Check stock availability again
            for item in items_snapshot:
                variant = ProductVariant.objects.select_for_update().get(id=item['variant_id'])
                if variant.stock < int(item['quantity']):
                    messages.error(request, f"Not enough stock for {variant.product.name}.")
                    transaction.set_rollback(True)
                    return redirect('basket_view')

            # Create final order record
            # order = Order.objects.create(
            #     user=request.user,
            #     shipping_address=shipping_address,
            #     subtotal=subtotal,
            #     total=total,
            #     original_total=subtotal,
            #     discount_amount=discount_amount,
            #     payment_method='razorpay',
            #     razorpay_order_id=razorpay_order_id,
            #     razorpay_payment_id=payment_id,
            #     payment_status='paid',
            #     amount_paid=total,
            #     status='confirmed',
            # )

            applied_coupon_if_any = None
            coupon_code = request.session.get('applied_coupon')
            if coupon_code:
                try:
                    applied_coupon_if_any = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
                except Coupon.DoesNotExist:
                    applied_coupon=None

            order = create_order_with_coupon(
                user=request.user,
                payment_method='razorpay',
                subtotal=Decimal(snapshot['subtotal']),
                total=Decimal(snapshot['total']),
                discount_amount=Decimal(snapshot['discount_amount']),
                address=snapshot['shipping_address'],
                coupon=applied_coupon_if_any,
                status='confirmed',
                payment_status='paid',
            )

            # Create order items & decrement stock
            for item in items_snapshot:
                variant = ProductVariant.objects.select_for_update().get(id=item['variant_id'])
                qty = int(item['quantity'])
                price = Decimal(item['price'])

                order.items.create(
                    variant=variant,
                    quantity=qty,
                    price=price
                )

                decrement_stock(variant, qty)

            # Mark items confirmed
            order.items.update(status='confirmed')

            # Clear basket
            # try:
            #     # basket = request.user.basket
            #     # basket.items.all().delete()
            #     # basket.is_active = False
            #     # basket.save()
            # except Exception:
            #     pass  # don't break success if basket cleanup fails

            # Clear Razorpay snapshot from session
            request.session.pop('razorpay_checkout', None)
            request.session.modified = True

            if applied_coupon_if_any:
                UserCoupon.objects.get_or_create(user=request.user, coupon=applied_coupon_if_any)

                # clearing coupn from session
                request.session.pop('applied_coupon_if_any', None)
                request.session.modified=True


        # --- Step 5: Redirect to Success ---
        messages.success(request, "Payment successful! Order placed successfully.")
        return redirect('order_success', order_id=order.id)

    except Exception as e:
        print("Payment handler error:", e)
        messages.error(request, "Something went wrong while processing your payment.")
        return render(request, 'order_failure.html')