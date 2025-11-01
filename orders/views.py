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
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter

from .models import Order, OrderItem
from .forms import CancelItemForm, CancelOrderForm, ReturnItemForm, AdminOrderStatusForm
from .utils import increment_stock, decrement_stock

from django.urls import reverse
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required

from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile

from wallet.utils import refund_to_wallet
from django.db import transaction
# Create your views here.


#order_success page

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


# order list with search and filter 
@login_required 
def order_list(request):
    """
    order list with search and filter options
    """

    orders = Order.objects.filter(user = request.user).order_by('-created_at', '-id')

    #search
    q = request.GET.get('q')
    if q:
        orders = orders.filter(Q(order_id__icontains=q) | Q(items__variant__product__name__icontains=q)).distinct()

    
    #filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    context = {
        'orders' : orders,
    }

    return render(request, "order_list.html", context)


@login_required
def order_details(request, order_id):
    """
    for order details
    """

    order = get_object_or_404(Order, id=order_id, user=request.user)

    progress_line_map = {
        'confirmed' : 25,
        'shipped' : 50,
        'out_for_delivery' :75,
        'delivered' : 100,
    }
    progress_percent = progress_line_map.get(order.status, 0)


    order_items = order.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images').all()    
    estimated_delivery = order.created_at + timedelta(days=7)

    #only allow owner or stff to view

    if order.user != request.user and not request.user.is_staff:
        raise Http404()



    active_items = order.items.filter(is_cancelled=False, is_returned=False)

    # for item in order_items:
    #     item.subtotal = item.price
    #     item.single_price = item.price / item.quantity

    # order_total = sum(item.subtotal for item in order_items)

    for item in order_items:
        item.total_price = item.price * item.quantity
    
    subtotal = sum(item.price * item.quantity for item in active_items)

    # subtotal = sum(item.subtotal for item in active_items)

    taxes = subtotal * Decimal('0')



    shipping=Decimal(0)
    discount=order.discount_amount or Decimal(0)

    total = subtotal + taxes + shipping - discount

    order_return_status = None
    statuses = order.items.filter(is_cancelled=False, is_returned=False).values_list('return_status', flat=True)
    
    context = {
        'order' : order,
        'order_items' : order_items ,
        # 'order_items' : active_items,
        'estimated_delivery' : estimated_delivery,
        'shipping_address' : order.shipping_address,
        'progress_percent' : progress_percent,
        'subtotal' : subtotal,
        'shipping' : shipping,
        'discount' : discount,
        'taxes' : taxes,
        'total' : total,
    }

    return render(request, "order_detail_page.html", context)



@login_required
def cancel_order(request, order_id):
    """
    to cancel the orders(before shipped), restore stock and update status
    """

    order = get_object_or_404(Order, id=order_id, user=request.user)
    user_email = order.user.email

    #to prevent double cancellation
    if order.status in ['cancelled', 'returned']:
        messages.info(request, "This order can't be cancelled.")
        return redirect('order_details', order_id=order.id)

    if order.status not in ['pending', 'processing', 'confirmed', 'partially_cancelled']:
        messages.error(request, "This oder can't be cancelled at this stage.")
        return redirect('order_details', order_id=order.id)

    # print("Order status:", order.status)

    print("Order:", order.id)
    print("Order status:", order.status)
    print("Payment method:", order.payment_method)
    print("Refund condition met?", order.payment_method.lower() in ['razorpay', 'wallet'])



    if request.method == 'POST':
        print("POST data:", request.POST)
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('reason')

            with transaction.atomic():
                
                orginal_paid_amount = order.total

                # cancel every ative (non-cancelled/non-returned) items in the order
                for item in order.items.filter(is_cancelled=False, is_returned=False):
                    increment_stock(item.variant, item.quantity)

                    # mark items as cancelled
                    item.is_cancelled = True
                    item.cancelled_reason = reason
                    item.cancelled_at = timezone.now()
                    item.save(update_fields=['is_cancelled', 'cancelled_reason', 'cancelled_at'])
                    print(f"Cancelling item {item.id} ({item.variant})")

                
                # order.recalc_total()
                # print("Now is :", {order.recalc_total})
                # order.status = 'cancelled'
                # order.is_returned = False
                # order.save(update_fields=['status', 'total', 'is_returned'])

                if order.payment_method.lower() in ['razorpay', 'wallet']:
                    from wallet.models import WalletTransaction

                    refund_desc = f"Refund for cancelled order #{order.id}"
                    already_refunded = WalletTransaction.objects.filter(
                        wallet__user=order.user,
                        description__icontains=f"order #{order.id}"
                    ).exists()

                    if not already_refunded:
                        refund_to_wallet(order.user, order.total, reason=refund_desc)
                        print(f"Refund issued for order {order.id}")
                    else:
                        print(f"Skipping duplicate refund for order {order.id}")

                order.recalc_total()
                order.status = 'cancelled'
                print("Before recalc:", order.total)
                order.is_returned = False
                print("After recalc:", order.total)

                order.save(update_fields=['status', 'total', 'is_returned'])
            
            messages.success(request, "Order cancelled.")
            # return redirect('order_details')
    else:
        form = CancelOrderForm()


    print("Order:", order.id)
    print("Order status:", order.status)
    print("Payment method:", order.payment_method)
    print("Refund condition met?", order.payment_method.lower() in ['razorpay', 'wallet'])

    context = {
        'order' : order,
        'form' : form,
        'user_email' : user_email,
    }

    return render(request, 'order_cancel_confirm.html', context)



@login_required
def return_order(request, order_id):
    
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.return_status == 'return_requested':
        messages.info(request, " Return request already submitted.")
        return redirect('order_details', order_id=order.id)

    reason = request.POST.get('reason', 'No reason provided')

    active_items = order.items.filter(is_cancelled=False, is_returned=False, status='delivered')

    if not active_items.exists():
        messages.warning(request, "No eligible items to return.")
        return render('order_details', order_id=order.id)


    for item in active_items:
        item.return_status = 'return_requested'
        item.return_at = timezone.now()
        item.return_reason = reason
        item.save(update_fields=['return_status', 'return_reason', 'return_at'])

    # # order-level return status
    # order.return_status = 'return_requested'
    # order.save(update_fields=['return_status'])

    order.update_return_status()

    messages.success(request, "Return request submitted for the admin to approve.")
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
                messages.warning(request, "This item has already been cancelled")
                return redirect('order_details' ,  order_id=order.id)

            with transaction.atomic():
                #restocking
                increment_stock(item.variant, item.quantity)

                #update cancellation info
                item.is_cancelled = True
                item.status = 'cancelled'
                item.cancelled_reason = reason
                item.cancelled_at = timezone.now()
                item.save(update_fields=['is_cancelled', 'status' ,'cancelled_reason', 'cancelled_at'])

                if order.payment_method in ['wallet', 'razorpay']:

                    from wallet.models import WalletTransaction

                    #unique identifier for the order item to refund
                    refund_reason = f"Cancelled Order Item #{item.id} (Order #{order.id})"
                    refund_amount = item.price * item.quantity


                    
                    already_refunded = WalletTransaction.objects.filter(wallet__user=order.user, description__icontains=refund_reason).exists()

                    if not already_refunded:
                        refund_to_wallet(order.user, refund_amount, reason=refund_reason)

                #update order total
                order.recalc_total()

                #update overall order status
                order.update_status()

            messages.success(request, f"{item.variant} has been cancelled successfully.")
            return redirect('order_details',order_id=order.id)

    return redirect('order_details', order_id = order.id)

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
    'pending' : ['confirmed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'partially_cancelled'],
    'confirmed' : ['shipped', 'out_for_delivery', 'delivered', 'cancelled', 'partially_cancelled'],
    'shipped' : ['out_for_delivery', 'cancelled', 'delivered'],
    'out_for_delivery' : ['delivered', 'cancelled'],
    'delivered' : ['returned'],
    'cancelled' : [],
    'returned' : [],
}


RETURN_TRANSITION_ALLOWED = {
    'pending' : ['return_requested'],
    'return_requested' : ['return_approved', 'return_rejected'],
    'return_approved' : [],
    'return_rejected' : [],
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


    #getting query search result
    q = request.GET.get('q')

    if q:
        orders = orders.filter(Q(order_id__icontains=q) | Q(user__email__icontains=q) | Q(items__variant__products__name__icontains=q)).distinct()

    #filter based on status
    status = request.GET.get('status')

    if status:
        orders = orders.filter(status=status)

    
    #pagination

    paginator = Paginator(orders, 10)
    page_no = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_no)

    context = {
        'orders' : page_obj.object_list,
        'page_obj' : page_obj,
        'q' : q or '',
        'status' : status or '',
    }

    return render(request, 'admin_order_list.html', context)


@staff_member_required
def admin_order_detail(request, id):
    """
    TO  show the single order details and status change for staffs
    """

    order = get_object_or_404(Order, id=id)

    order_items = order.items.select_related('variant', 'variant__product').all()

    #to get subtotal for each items (if there are 2 * product)
    for item in order_items:
        item.subtotal = item.price
        item.single_price = item.price / item.quantity

    order_total = sum(item.subtotal for item in order_items)

    #prepare form prefilled with current status
    form = AdminOrderStatusForm(initial={'status' : order.status})
    discount_applied = order.discount_amount or 0
    return_items = order.items.filter(return_status__in=['return_requested', 'return_approved', 'return_rejected'])


    # return_requests = ReturnRequest.objects.filter(item__order=order)

    context = {
        'order' : order,
        'order_items' : order_items,
        'order_total' : order_total,
        'form' : form,
        # 'return_requests' : return_requests
        'return_items': return_items,
        'discount_applied' : discount_applied,
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
        for m in form.errors.get('__all__', []): #__all__ is a special key in form.errors in django forms
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

        #cancelling: restore the stockk and to mark every non cancelled or no returned item cancelled
        if new_status == 'cancelled':

            for item in order.items.filter(is_cancelled=False, is_returned=False):
                increment_stock(item.variant, item.quantity)
                item.is_cancelled = True
                item.cancelled_reason = reason
                item.cancelled_at = timezone.now()
                item.save(update_fields=['is_cancelled', 'cancelled_reason', 'cancelled_at'])

            order.status = 'cancelled'
            order.recalc_total()
            order.save(update_fields=['status', 'total'])
            messages.success(request, f"Order {order.order_id} marked as cancelled.")

        #Returning: allowed only if delivered, mark items returned and restore stock
        elif new_status == 'returned':

            if current_status != 'delivered':
                messages.error(request, "Can only mark returned when order is delivered.")
                return redirect('admin_order_detail', id=order.id)

            for item in order.items.filter(is_returned=False, is_cancelled=False):
                increment_stock(item.variant, item.quantity)
                item.is_returned=True
                item.returned_reason=reason
                item.returned_at = timezone.now()
                item.save(update_fields=['is_returned', 'returned_reason','returned_at'])

            total_refund = sum(item.price * item.quantity for item in order.items.filter(is_cancelled=False, is_returned=True))
            if order.payment_method in ['razorpay', 'wallet']:
                refund_to_wallet(order.user, total_refund, reason=f"Refund for returned order {order.order_id}")

            order.status = 'returned'
            order.recalc_total()
            order.save(update_fields=['status', 'total'])
            messages.success(request, f"Order {order.order_id} marked as returned.")

        
        #confirmed

        elif new_status == 'confirmed':

            order.status = 'confirmed'
            order.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} confirmed.")

        #shipped
        elif new_status in ['shipped', 'out_for_delivery', 'delivered']:

            order.status = new_status
            order.save(update_fields=['status'])


            if new_status == 'delivered':
                for item in order.items.filter(is_cancelled=False, is_returned=False):
                    item.status = 'delivered'
                    item.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} updated to {new_status}.")

        
        # elif new_status 
        else:

            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} updated.")

    return redirect('admin_order_detail', id=order.id)




@staff_member_required
def admin_return_process(request, item_id):
    """
    Admin approves or rejects a return request.
    """
    item = get_object_or_404(OrderItem, id=item_id)
    action = request.POST.get('action')

    if action == 'approve':
        item.return_status = 'return_approved'
        item.is_returned = True
        item.status = 'returned'
        item.returned_at = timezone.now()
        increment_stock(item.variant, item.quantity)
        messages.success(request, f"Return approved for {item.variant.product.name}.")

        if item.order.payment_method in ['razorpay', 'wallet']:
            refund_to_wallet(item.order.user, item.price * item.quantity, reason=f"Refund for returned item {item.variant}")
    elif action == 'reject':
        item.return_status = 'return_rejected'
        messages.warning(request, f"Return rejected for {item.variant.product.name}.")
    else:
        messages.error(request, "Invalid action.")
        return redirect('admin_order_detail', id=item.order.id)

    item.save(update_fields=['return_status', 'is_returned', 'status', 'return_at'])

    item.order.update_return_status()

    return redirect('admin_order_detail', id=item.order.id)



# def update_order_status(self):
#     """
#     to sync order status based on all item status
#     """

#     # order = self.order
#     item_statuses = list(order.items.values_list('status', flat=True))

#     if all(s == 'delivered' for s in item_statuses):
#         order.status = 'delivered'

#     elif all(s == 'cancelled' for s in item_statuses):
#         order.status = 'cancelled'

#     elif any(s in ['shipped', 'out_for_delivery'] for s in item_statuses):
#         order.status = 'out_for_delivery' if 'out_for_delivery' in item_statuses else 'shipped'
    
#     elif any(s == 'confirmed' for s in item_statuses):
#         order.status = 'confirmed'
    
#     elif any(s in ['cancelled', 'returned'] for s in item_statuses):
#         order.status = 'partially_cancelled'
    
#     else:
#         order.status = 'pending'
    
#     order.save(update_fields=['status'])


# def cancel(self, reason=None):
#     """
#     cancel a single item and restore stock
#     """

#     if not self.is_cancelled:
#         self.is_cancelled = True
#         self.status = 'cancelled'
#         self.cancelled_reason = reason
#         self.cancelled_at = timezone.now()
#         self.variant.stock += self.quantity
#         self.variant.save(update_fields=['stock'])
#         self.save()

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

    #handling return_status updates

    if new_return_status:
        current_return = item.return_status
        if not is_return_transition_allowed(current_return, new_return_status):
            messages.error(request, f"Invalid return transition")
            return redirect('admin_order_detail', id=order.id)

        
        item.return_status = new_return_status

        if new_return_status == 'return_approved':
            item.is_returned = True
            item.return_at = timezone.now()
            item.status = "returned"
            increment_stock(item.variant, item.quantity)
            refund_to_wallet(user, item.item_total, reason=f"Refund for returned item {item.variant}")
            messages.success(request, f"Return approved and refunded for  {item.variant}.")

        elif new_return_status == 'return_rejected':
            messages.info(request, f"Return rejected for {item.variant}.")

        item.save(update_fields=['return_status', 'is_returned', 'return_at', 'status'])
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
            refund_to_wallet(user, item.item_total, reason=f"Refund for cancelled item {item.variant}")
        messages.success(request, f"Item {item.variant} cancelled and refunded.")

    elif new_status == 'returned':
        item.is_returned = True
        item.return_at = timezone.now()
        item.return_reason = reason
        increment_stock(item.variant, item.quantity)
        if order.payment_method in ['wallet', 'razorpay']:
            refund_to_wallet(user, item.item_total, reason= f"Refund for cancelled item {item.variant}")
        messages.success(request, f"Item {item.variant} returned.")
    
    elif new_status == 'delivered':
        messages.success(request, f"Item {item.variant} marked as delivered.")

    item.status = new_status
    
    item.save(update_fields=['status', 'is_cancelled', 'cancelled_reason', 'cancelled_at', 'is_returned', 'return_reason', 'return_at'])

    # remaining = order.items.exclude(status__in=['cancelled', 'returned']).count()
    # if remaining == 0:
    #     order.status = "cancelled"
    # elif all(i.status == 'delivered' for i in order.items.all()):
    #     order.status = "delivered"
    # order.save(update_fields=['status'])

    order.update_order_status()
    order.refresh_from_db()
    messages.success(request, f"{item.variant} status updated to {new_status}.")
    return redirect('admin_order_detail', id=order.id)

@login_required
def download_invoice(request, order_id):
    """
    to generate and download PDF invoice for an order
    """

    #getting order first
    order = get_object_or_404(Order, id=order_id, user=request.user)

    #gertting orders itam
    order_items = order.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images').all()

    #tax and shipping calculation
    subtotal = sum(item.price * item.quantity for item in order_items)

    shipping = Decimal('0')
    discount = Decimal('0')
    taxes = subtotal * Decimal('0.12')
    total = subtotal + taxes + shipping - discount


    context = {
        'order' : order,
        'order_items' : order_items,
        'subtotal' : subtotal,
        'tax_amount' : taxes,
        'shipping' : shipping,
        'company_name' : 'POWERBLEND',
        'company_address' : 'Ottapalam, Palakkad. Kerala - 679102',
        'company_phone' : '+91 9061752197',
        'company_email' : 'support@powerblend.com',
        'company_website': 'www.powerblend.com',
    }

    #render HTML template
    html_string = render_to_string('invoice.html', context)

    #generate pdf
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    result = html.write_pdf()

    #create HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="POWERBLEND_Invoice_{order.order_id}.pdf"'
    response['Content-Transfer-Encoding'] = 'binary'
    response.write(result)

    return response


