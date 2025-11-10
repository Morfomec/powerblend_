from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, Http404
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta, date
import io
from decimal import Decimal
from django.contrib import messages
from .models import Order, OrderItem
from .forms import CancelItemForm, CancelOrderForm, ReturnItemForm, AdminOrderStatusForm
from .utils import increment_stock, decrement_stock, calculate_strict_voucher_refund
from django.urls import reverse
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
from wallet.utils import refund_to_wallet
from wallet.models import WalletTransaction
from django.db import transaction
# Create your views here.


# order_success page

@login_required
def order_success(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Calculate estimated delivery (e.g., 7 days from now)

    estimated_delivery = order.created_at + timedelta(days=7)

    context = {
        'order': order,
        'estimated_delivery': estimated_delivery,
    }
    return render(request, 'order_success.html', context)


@login_required
def order_failure(request):
    # Get error message from session or query parameter
    error_message = request.session.get(
        'payment_error', 'Payment could not be completed')

    # Clear the error from session
    if 'payment_error' in request.session:
        del request.session['payment_error']

    context = {
        'error_message': error_message,
    }
    return render(request, 'order_failure.html', context)


# order list with search and filter
@login_required
def order_list(request):
    """
    order list with search and filter options
    """

    orders = Order.objects.filter(
        user=request.user).order_by(
        '-created_at',
        '-id')

    # search
    q = request.GET.get('q')
    if q:
        orders = orders.filter(Q(order_id__icontains=q) | Q(
            items__variant__product__name__icontains=q)).distinct()

    # filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    # pagination

    paginator = Paginator(orders, 10)
    page_no = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_no)

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'q': q or '',
        'status': status or '',
    }

    return render(request, "order_list.html", context)


@login_required
def order_details(request, order_id):
    """
    for order details
    """

    order = get_object_or_404(Order, id=order_id, user=request.user)

    progress_line_map = {
        'confirmed': 25,
        'shipped': 50,
        'out_for_delivery': 75,
        'delivered': 100,
    }
    progress_percent = progress_line_map.get(order.status, 0)

    order_items = order.items.select_related(
        'variant', 'variant__product').prefetch_related('variant__product__images').all()
    estimated_delivery = order.created_at + timedelta(days=7)

    for item in order_items:
        item.single_price = item.price / item.quantity
    # only allow owner or stff to view

    if order.user != request.user and not request.user.is_staff:
        raise Http404()

    active_items = order.items.filter(is_cancelled=False, is_returned=False)

    for item in order_items:
        item.subtotal = item.price
        item.single_price = item.price / item.quantity

    subtotal = sum(item.price for item in active_items)

    taxes = subtotal * Decimal('0')

    shipping = Decimal(0)
    discount = order.discount_amount or Decimal(0)

    total = subtotal + taxes + shipping - discount

    order_return_status = None
    statuses = order.items.filter(
        is_cancelled=False,
        is_returned=False).values_list(
        'return_status',
        flat=True)

    context = {
        'order': order,
        'order_items': order_items,
        # 'order_items' : active_items,
        'estimated_delivery': estimated_delivery,
        'shipping_address': order.shipping_address,
        'progress_percent': progress_percent,
        'subtotal': subtotal,
        'shipping': shipping,
        'discount': discount,
        'taxes': taxes,
        'total': total,
    }

    return render(request, "order_detail_page.html", context)


@login_required
def cancel_order(request, order_id):
    """
    to cancel the orders(before shipped), restore stock and update status
    """

    order = get_object_or_404(Order, id=order_id, user=request.user)
    user_email = order.user.email

    # to prevent double cancellation
    if order.status in ['cancelled', 'returned']:
        messages.info(request, "This order can't be cancelled.")
        return redirect('order_details', order_id=order.id)

    if order.status not in [
        'pending',
        'processing',
        'confirmed',
            'partially_cancelled']:
        messages.error(request, "This oder can't be cancelled at this stage.")
        return redirect('order_details', order_id=order.id)

    # print("Order status:", order.status)

    print("Order:", order.id)
    print("Order status:", order.status)
    print("Payment method:", order.payment_method)
    print(
        "Refund condition met?",
        order.payment_method.lower() in [
            'razorpay',
            'wallet'])

    if request.method == 'POST':
        print("POST data:", request.POST)
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('reason')

            with transaction.atomic():
                # --- STEP 1: Cancel items and restock ---
                active_items = order.items.filter(
                    is_cancelled=False, is_returned=False)
                for item in active_items:
                    increment_stock(item.variant, item.quantity)
                    item.is_cancelled = True
                    item.cancelled_reason = reason
                    item.cancelled_at = timezone.now()
                    item.status = "cancelled"
                    item.save(
                        update_fields=[
                            "is_cancelled",
                            "cancelled_reason",
                            "cancelled_at",
                            "status"])

                # --- STEP 2: Prepare refund variables ---
                amount_paid = Decimal(order.amount_paid or 0)
                refunded_so_far = Decimal(order.refunded_amount or 0)
                refundable_balance = amount_paid - refunded_so_far

                refund_amount = Decimal("0.00")
                discount_revoked = False
                remaining_total = Decimal("0.00")

                # --- STEP 3: Refund logic ---
                if order.payment_method and order.payment_method.lower(
                ) in ["razorpay", "wallet"] and refundable_balance > 0:
                    # Collect cancelled items
                    cancelled_items = list(
                        order.items.filter(
                            is_cancelled=True))

                    # Apply strict rule
                    refund_amount, discount_revoked, remaining_total = calculate_strict_voucher_refund(
                        order, cancelled_items)
                    refund_amount = Decimal(
                        refund_amount).quantize(Decimal("0.01"))

                    # Cap refund to available refundable balance
                    refund_amount = min(refund_amount, refundable_balance)

                    # Check if refund already exists for this order
                    already_refunded = WalletTransaction.objects.filter(
                        wallet__user=order.user,
                        description__icontains=f"order #{order.id}"
                    ).exists()

                    if refund_amount > 0 and not already_refunded:
                        refund_reason = f"Refund for cancelled order #{
                            order.id}"
                        if discount_revoked:
                            refund_reason += " [Coupon Revoked]"

                        # Refund to wallet
                        refund_to_wallet(
                            order.user, refund_amount, reason=refund_reason)

                        # Update refunded amount
                        order.refunded_amount = refunded_so_far + refund_amount

                        # If coupon revoked, reset discounts and total
                        if discount_revoked:
                            order.coupon_discount = Decimal("0.00")
                            order.discount_amount = Decimal("0.00")
                            order.total = remaining_total

                        order.save(
                            update_fields=[
                                "refunded_amount",
                                "coupon_discount",
                                "discount_amount",
                                "total"])

                # --- STEP 4: Update order status ---
                order.recalc_total()
                order.status = "cancelled"
                order.is_returned = False
                order.save(update_fields=["status", "total", "is_returned"])

            messages.success(
                request, f"Order #{
                    order.order_id} cancelled successfully.")
            return redirect("order_details", order_id=order.id)
    else:
        form = CancelOrderForm()

    context = {
        "order": order,
        "form": form,
        "user_email": user_email,
    }
    return render(request, "order_cancel_confirm.html", context)


@login_required
def return_order(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.return_status == 'return_requested':
        messages.info(request, " Return request already submitted.")
        return redirect('order_details', order_id=order.id)

    reason = request.POST.get('reason', 'No reason provided')

    active_items = order.items.filter(
        is_cancelled=False,
        is_returned=False,
        status='delivered')

    if not active_items.exists():
        messages.warning(request, "No eligible items to return.")
        return render('order_details', order_id=order.id)

    for item in active_items:
        item.return_status = 'return_requested'
        item.return_at = timezone.now()
        item.return_reason = reason
        item.save(
            update_fields=[
                'return_status',
                'return_reason',
                'return_at'])

    order.update_return_status()

    messages.success(
        request,
        "Return request submitted for the admin to approve.")
    return redirect('order_details', order_id=order.id)


@login_required
def cancel_item(request, order_id):
    """
    cancel a single item in an order and issue the refund if applicable
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        form = CancelItemForm(request.POST)
        if form.is_valid():
            item_id = form.cleaned_data['item_id']
            reason = form.cleaned_data['reason']
            item = get_object_or_404(OrderItem, id=item_id, order=order)

            if item.is_cancelled:
                messages.warning(
                    request, "This item has already been cancelled")
                return redirect('order_details', order_id=order.id)

            with transaction.atomic():
                # restocking
                increment_stock(item.variant, item.quantity)

                # update cancellation info
                item.is_cancelled = True
                item.status = 'cancelled'
                item.cancelled_reason = reason
                item.cancelled_at = timezone.now()
                item.save(
                    update_fields=[
                        'is_cancelled',
                        'status',
                        'cancelled_reason',
                        'cancelled_at'])

                affected_items = [item]
                refund_amount, discount_revoked, remaining_total = calculate_strict_voucher_refund(
                    order, affected_items)

                if refund_amount > 0 and order.payment_method in [
                        'wallet', 'razorpay']:
                    from wallet.models import WalletTransaction

                    refund_reason = f"Cancelled Order Item #{
                        item.id} (Order #{
                        order.id})"
                    already_refunded = WalletTransaction.objects.filter(
                        wallet__user=order.user,
                        description__icontains=refund_reason
                    ).exists()

                    if not already_refunded:
                        refund_to_wallet(
                            order.user, refund_amount, reason=refund_reason)

                # Recalculate order total and update order status
                order.recalc_total()
                order.update_status()

                # If coupon is revoked, remove it from the order
                if discount_revoked:
                    order.coupon_code = None
                    order.coupon_discount = Decimal("0.00")
                    order.save(
                        update_fields=[
                            'coupon_code',
                            'coupon_discount'])
                    messages.info(
                        request,
                        "The coupon has been revoked due to order value falling below the threshold.")

            messages.success(
                request, f"{
                    item.variant} has been cancelled successfully.")
            return redirect('order_details', order_id=order.id)

    return redirect('order_details', order_id=order.id)


@login_required
def return_item(request, order_id, item_id):
    """
    return a single item (only if  delivered)

    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if item.status != 'delivered':
        messages.error(request, "This item is not delivered yet.")
        return redirect('order_details', order_id=order.id)

    if item.return_status in ['return_requested', 'return_approved']:
        messages.info(request, "Return already requested or approved.")
        return redirect('order_details', order_id=order.id)

        # Mark as requested
    item.return_status = 'return_requested'
    item.return_reason = request.POST.get('reason', '')
    item.return_at = timezone.now()
    item.save(update_fields=['return_status', 'return_reason', 'return_at'])

    messages.success(request, 'Return request sent for admin approval.')
    return redirect('order_details', order_id=order.id)


######################### ADMIN SIDE #########################
ADMIN_ALLOWED_TRANSITIONS = {
    'pending': [
        'confirmed',
        'shipped',
        'out_for_delivery',
        'delivered',
        'cancelled',
        'partially_cancelled'],
    'confirmed': [
        'shipped',
        'out_for_delivery',
        'delivered',
        'cancelled',
        'partially_cancelled'],
    'shipped': [
        'out_for_delivery',
        'cancelled',
        'delivered'],
    'out_for_delivery': [
        'delivered',
        'cancelled'],
    'delivered': ['returned'],
    'cancelled': [],
    'returned': [],
}


RETURN_TRANSITION_ALLOWED = {
    'pending': ['return_requested'],
    'return_requested': ['return_approved', 'return_rejected'],
    'return_approved': [],
    'return_rejected': [],
}


def is_return_transition_allowed(current, target):
    return target in RETURN_TRANSITION_ALLOWED.get(current, [])


def is_admin_transition_allowed(current, target):
    return target in ADMIN_ALLOWED_TRANSITIONS.get(current, [])


@staff_member_required
def admin_order_list(request):
    """
    Staff-only: list orders with search and status filter.
    """

    orders = Order.objects.all().order_by('-created_at', '-id')

    # getting query search result
    q = request.GET.get('q')

    if q:
        orders = orders.filter(Q(order_id__icontains=q) | Q(user__email__icontains=q) | Q(
            items__variant__product__name__icontains=q)).distinct()

    # filter based on status
    status = request.GET.get('status')

    if status:
        orders = orders.filter(status=status)

    # pagination

    paginator = Paginator(orders, 10)
    page_no = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_no)

    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'q': q or '',
        'status': status or '',
    }

    return render(request, 'admin_order_list.html', context)


@staff_member_required
def admin_order_detail(request, id):
    """
    TO  show the single order details and status change for staffs
    """

    order = get_object_or_404(Order, id=id)

    order_items = order.items.select_related(
        'variant', 'variant__product').all()

    # to get subtotal for each items (if there are 2 * product)
    for item in order_items:
        item.subtotal = item.price
        item.single_price = item.price / item.quantity

    actual_amount = sum(item.subtotal for item in order_items)

    # prepare form prefilled with current status
    form = AdminOrderStatusForm(initial={'status': order.status})
    discount_applied = order.discount_amount or 0

    total_amount = actual_amount - discount_applied
    return_items = order.items.filter(
        return_status__in=[
            'return_requested',
            'return_approved',
            'return_rejected'])

    # return_requests = ReturnRequest.objects.filter(item__order=order)

    context = {
        'order': order,
        'order_items': order_items,
        'actual_amount': actual_amount,
        'total_amount': total_amount,
        'return_items': return_items,
        'discount_applied': discount_applied,
    }

    return render(request, 'admin_order_detail.html', context)


@staff_member_required
def admin_update_order_status(request, id):
    """
    to handles the post to change the order status from the admin panel and
    to increment or decrement the the stock upon cancel/return, also to recalc totals.

    handles order-level status changes, including setting an order to 'returned'.
    """

    order = get_object_or_404(Order, id=id)

    if request.method != 'POST':
        messages.error(request, "Invalid request method!!")
        return redirect('admin_order_detail', id=order.id)

    form = AdminOrderStatusForm(request.POST)
    if not form.is_valid():
        for m in form.errors.get(
            '__all__',
                []):  # __all__ is a special key in form.errors in django forms
            messages.error(request, m)
        return redirect('admin_order_detail', id=order.id)

    new_status = form.cleaned_data['status']
    reason = form.cleaned_data.get('reason', '').strip()
    current_status = order.status

    # checking if transition allowed or not

    if not is_admin_transition_allowed(current_status, new_status):
        messages.error(request, f"Transition not allowed: {current_status}")
        return redirect('admin_order_detail', id=order.id)

    with transaction.atomic():

        # cancelling: restore the stockk and to mark every non cancelled or no
        # returned item cancelled
        if new_status == 'cancelled':

            for item in order.items.filter(
                    is_cancelled=False, is_returned=False):
                increment_stock(item.variant, item.quantity)
                item.is_cancelled = True
                item.cancelled_reason = reason
                item.cancelled_at = timezone.now()
                item.save(
                    update_fields=[
                        'is_cancelled',
                        'cancelled_reason',
                        'cancelled_at'])

            order.status = 'cancelled'
            order.recalc_total()
            order.save(update_fields=['status', 'total'])
            messages.success(
                request, f"Order {
                    order.order_id} marked as cancelled.")

        # Returning: allowed only if delivered, mark items returned and restore
        # stock
        elif new_status == 'returned':

            if current_status != 'delivered':
                messages.error(
                    request, "Can only mark returned when order is delivered.")
                return redirect('admin_order_detail', id=order.id)

            for item in order.items.filter(
                    is_returned=False, is_cancelled=False):
                increment_stock(item.variant, item.quantity)
                item.is_returned = True
                item.returned_reason = reason
                item.returned_at = timezone.now()
                item.save(
                    update_fields=[
                        'is_returned',
                        'returned_reason',
                        'returned_at'])

            total_refund = sum(
                item.price *
                item.quantity for item in order.items.filter(
                    is_cancelled=False,
                    is_returned=True))
            if order.payment_method in ['razorpay', 'wallet']:
                refund_to_wallet(
                    order.user,
                    total_refund,
                    reason=f"Refund for returned order {
                        order.order_id}")

            order.status = 'returned'
            order.recalc_total()
            order.save(update_fields=['status', 'total'])
            messages.success(
                request, f"Order {
                    order.order_id} marked as returned.")

        # confirmed

        elif new_status == 'confirmed':

            order.status = 'confirmed'
            order.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} confirmed.")

        # shipped
        elif new_status in ['shipped', 'out_for_delivery', 'delivered']:

            order.status = new_status
            order.save(update_fields=['status'])

            if new_status == 'delivered':
                for item in order.items.filter(
                        is_cancelled=False, is_returned=False):
                    item.status = 'delivered'
                    item.save(update_fields=['status'])
            messages.success(
                request, f"Order {
                    order.order_id} updated to {new_status}.")

        # elif new_status
        else:

            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} updated.")

    return redirect('admin_order_detail', id=order.id)


@transaction.atomic
@staff_member_required
def admin_update_item_status(request, item_id):
    """
    Admin can update individual OrderItems status
    """

    item = get_object_or_404(OrderItem, id=item_id)
    order = item.order
    user = order.user

    if request.method != 'POST':
        messages.error(request, " Invalid request method")
        return redirect('admin_order_detail', id=order.id)

    new_status = request.POST.get("status")
    new_return_status = request.POST.get("return_status")
    reason = request.POST.get("reason", "").strip()

    # handling return_status updates

    if new_return_status:
        current_return = item.return_status
        if not is_return_transition_allowed(current_return, new_return_status):
            messages.error(request, f"Invalid return transition")
            return redirect('admin_order_detail', id=order.id)

        item.return_status = new_return_status

        if new_return_status == 'return_approved':
            from wallet.models import WalletTransaction
            from .utils import calculate_strict_voucher_refund
            from decimal import Decimal

            item.is_returned = True
            item.return_at = timezone.now()
            item.status = "returned"
            increment_stock(item.variant, item.quantity)
            item.save(
                update_fields=[
                    'return_status',
                    'is_returned',
                    'status',
                    'return_at'])

            # --- Voucher-aware refund ---
            order.recalc_total()  # keep totals fresh
            affected_items = [item]
            refund_amount, discount_revoked, remaining_total = calculate_strict_voucher_refund(
                order, affected_items)

            refund_reason = f"Refund for returned item #{
                item.id} (Order #{
                order.id})"
            already_refunded = WalletTransaction.objects.filter(
                wallet__user=order.user,
                description__icontains=f"returned item #{item.id}"
            ).exists()

            if refund_amount > 0 and order.payment_method in [
                    'wallet', 'razorpay'] and not already_refunded:
                refund_to_wallet(
                    order.user,
                    refund_amount,
                    reason=refund_reason)
                messages.success(
                    request, f"Refund of ₹{refund_amount} processed to wallet.")
            elif already_refunded:
                messages.info(
                    request, "Refund already processed previously for this item.")

            # If coupon revoked, clear it
            if discount_revoked:
                order.coupon_code = None
                order.coupon_discount = Decimal("0.00")
                order.coupon_min_amount = Decimal("0.00")
                order.save(
                    update_fields=[
                        'coupon_code',
                        'coupon_discount',
                        'coupon_min_amount'])
                messages.info(
                    request, "Coupon revoked — remaining order value fell below threshold.")

            messages.success(request, f"Return approved for {item.variant}.")

        elif new_return_status == 'return_rejected':
            messages.info(request, f"Return rejected for {item.variant}.")

        item.save(
            update_fields=[
                'return_status',
                'is_returned',
                'return_at',
                'status'])
        return redirect('admin_order_detail', id=order.id)

    # handle normal statu updates
    current_status = item.status
    if not is_admin_transition_allowed(current_status, new_status):
        messages.error(request, f"Invalid status transition")
        return redirect('admin_order_detail', id=order.id)

    if new_status == 'cancelled':
        item.is_cancelled = True
        item.cancelled_at = timezone.now()
        item.cancelled_reason = reason
        increment_stock(item.variant, item.quantity)

        if order.payment_method in ['wallet', 'razorpay']:
            refund_to_wallet(
                user,
                item.item_total,
                reason=f"Refund for cancelled item {
                    item.variant}")
        messages.success(
            request, f"Item {
                item.variant} cancelled and refunded.")

    elif new_status == 'returned':
        item.is_returned = True
        item.return_at = timezone.now()
        item.return_reason = reason
        increment_stock(item.variant, item.quantity)
        if order.payment_method in ['wallet', 'razorpay']:
            refund_to_wallet(
                user,
                item.item_total,
                reason=f"Refund for cancelled item {
                    item.variant}")
        messages.success(request, f"Item {item.variant} returned.")

    elif new_status == 'delivered':
        messages.success(request, f"Item {item.variant} marked as delivered.")

    item.status = new_status

    item.save(
        update_fields=[
            'status',
            'is_cancelled',
            'cancelled_reason',
            'cancelled_at',
            'is_returned',
            'return_reason',
            'return_at'])

    order.update_order_status()
    order.refresh_from_db()
    messages.success(
        request, f"{
            item.variant} status updated to {new_status}.")
    return redirect('admin_order_detail', id=order.id)


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Show ALL items in table (including cancelled/returned)
    order_items = order.items.all()

    # Only count non-cancelled for totals
    active_items = order.items.filter(is_cancelled=False, is_returned=False)

    # Add unit_price and subtotal fields
    for item in order_items:
        item.unit_price = item.price / item.quantity
        item.subtotal = item.price

    # Totals
    subtotal = sum(item.price for item in active_items)
    discount = (order.discount_amount or Decimal('0')) + \
        (order.coupon_discount or Decimal('0'))
    shipping = Decimal('0')
    total = subtotal + shipping - discount

    context = {
        "order": order,
        "order_items": order_items,
        "subtotal": subtotal,
        "discount": discount,
        "shipping": shipping,
        "total": total,
        'company_name': 'POWERBLEND',
        'company_address': 'Ottapalam, Palakkad. Kerala - 679102',
        'company_phone': '+91 9061752197',
        'company_email': 'support@powerblend.com',
        'company_website': 'www.powerblend.com',
    }

    html_string = render_to_string("invoice.html", context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="POWERBLEND_Invoice_{
        order.order_id}.pdf"'
    return response
