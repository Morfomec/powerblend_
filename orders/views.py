from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, Http404
from django.db.models import Q 
from django.utils import timezone
from datetime import timedelta
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

    order_items = order.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images').all()    
    estimated_delivery = order.created_at + timedelta(days=7)

    #only allow owner or stff to view

    if order.user != request.user and not request.user.is_staff:
        raise Http404()

    basket = getattr(request.user, 'basket', None)
    #tax and shipping calculation
    subtotal = basket.total_price * Decimal('0.95')

    shipping = Decimal('0')
    discount = Decimal('0')
    taxes = subtotal * Decimal('0.12')
    total = subtotal + taxes + shipping - discount

    context = {
        'order' : order,
        'order_items' : order_items ,
        'estimated_delivery' : estimated_delivery,
        'shipping_address' : order.shipping_address,

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
    
    #to prevent double cancellation
    if order.status in ['cancelled', 'returned']:
        messages.info(request, "This order can't be cancelled.")
        return redirect('order_details', id=order.order_id)

    if order.status not in ['pending', 'processing']:
        messages.error(request, "This oder can't be cancelled.")
        return redirect('order_details', id=order.order_id)

    print("Order status:", order.status)


    if request.method == 'POST':
        print("POST data:", request.POST)
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('reason')

            with transaction.atomic():

                # cancel every ative (non-cancelled/non-returned) items in the order
                for item in order.items.filter(is_cancelled=False, is_returned=False):
                    increment_stock(item.variant, item.quantity)

                    # mark items as cancelled
                    item.is_cancelled = True
                    item.cancelled_reason = reason
                    item.cancelled_at = timezone.now()
                    item.save(update_fields=['is_cancelled', 'cancelled_reason', 'cancelled_at'])
                    print(f"Cancelling item {item.id} ({item.variant})")

                
                order.status = 'cancelled'
                print("Before recalc:", order.total)
                order.recalc_total()
                print("After recalc:", order.total)

                order.save(update_fields=['status', 'total'])
            
            messages.success(request, "Order cancelled and stock updated.")
            # return redirect('order_details')
    else:
        form = CancelOrderForm()

    context = {
        'order' : order,
        'form' : form,
    }

    return render(request, 'order_cancel_confirm.html', context)


@login_required
def cancel_item(request, order_id):
    """
    cancel a single item
    """
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if request.method == 'POST':
        form = CancelItemForm(request.POST)
        if form.is_valid():
            item = get_object_or_404(OrderItem, id=form.cleaned_data['itme_id'], order=order)
            
            if item.is_cancelled:
                return redirect('order_details' ,  order_id=order.order_id)

            with transaction.atomic():
                increment_stock(item.variant, item.quantity)
                item.is_returned = True
                item.returned_reason = form.cleaned_data('reason')
                item.returned_at = timezone.now()
                item.save(update_fields=['is_cancelled', 'cancelled_reason', 'cancelled_at'])

                order.recalc_total()

            return redirect('order_details',order_id=order.order_id)

    return redirect('order_details', order_id = order.order_id)

@login_required
def return_item(request, order_id): 
    """
    return a single item (only if  delivered)
    """

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    #to make sure only delivered products can  be returned

    if order.status != 'delivered':
        return redirect('order_details', order_id=order.order_id)

    if request.method == 'POST':
        form = ReturnItemForm(request.POST)
        if form.is_valid():
            item = get_object_or_404(OrderItem, id=form.cleaned_data['item_id'], order=order)
        
        #if already returned
        if item.is_returned:
            return redirect('order_details', order_id=order.order_id)

        with transaction.atomic():
            increment_stock(item.variant, item.quantity)
            item.is_returned = True
            item.returned_reason = form.cleaned_data['reason']
            item.returned_at  = timezone.now()
            item.save(update_fields=['is_returned', 'returned_reason', 'returned_at'])

            # if all itmes are either cancelled or returned , will mark whole order as returned
            if not order.items.filter(is_cancelled=False, is_returned=False).exists():
                order.status = 'returned'
                order.save(update_fields=['status'])
        
        return redirect('order_details', order_id=order.order_id)
    
    return redirect('order_details', order_id=order.order_id)







######################### ADMIN SIDE #########################


ALLOWED_TRANSITIONS = {
    'pending' : ['confirmed', 'cancelled'],
    'confirmed' : ['shipped', 'cancelled'],
    'shipped' : ['delivered'],
    'delivered' : ['returned'],
    'cancelled' : [],
    'returned' : [],
}


def is_transition_allowed(current, target):
    return target in ALLOWED_TRANSITIONS.get(current, [])


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

    #prepare form prefilled with current status
    form = AdminOrderStatusForm(initial={'status' : order.status})

    context = {
        'order' : order,
        'order_items' : order_items,
        'form' : form,
    }

    return render(request, 'admin_order_detail.html', context)

@staff_member_required
def admin_update_order_status(request, id):
    """
    to handles the post to change the order status from the admin panel and
    to increment or decrement the the stock upon cancel/return, also to recalc totals.
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

    if not is_transition_allowed(current_status, new_status):
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
        elif new_status in ['shipped', 'delivered']:

            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} updated to {new_status}.")

        else:

            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f"Order {order.order_id} updated.")

    return redirect('admin_order_detail', id=order.id)