from django.db.models import F 
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

# Increment stock(when cancelling or returning)
def increment_stock(variant, qty):
    variant.stock = F ('stock') + qty
    variant.save(update_fields= ['stock'])
    variant.refresh_from_db()


#decrement stock when placing an order
def decrement_stock(variant, qty):
    variant.stock = F('stock') - qty
    variant.save(update_fields=['stock'])



# def calculate_proportional_refund(order, item):
#     """
#     Refund based on SUBTOTAL pricing (item.price already includes qty).
#     Refund only the paid part (after discounts, wallet, etc).
#     """

    # original_total = Decimal(order.original_total or order.total or 0)
    # amount_paid = Decimal(order.amount_paid or 0)

    # if original_total <= 0 or amount_paid <= 0:
    #     return Decimal('0.00')

    # # What % of the cart was actually paid?
    # paid_ratio = amount_paid / original_total

    # # ✅ item.price is already SUBTOTAL (qty included)
    # item_value = Decimal(item.price) * item.quantity

    # refund = (item_value * paid_ratio).quantize(
    #     Decimal('0.01'),
    #     rounding=ROUND_HALF_UP
    # )

    # # Never refund more than remaining payable amount
    # return min(refund, amount_paid - Decimal(order.refunded_amount or 0))


    # order_paid = Decimal(order.amount_paid or 0)
    # refunded_so_far = Decimal(order.refunded_amount or 0)
    # order_subtotal = sum((i.price for i in order.items.all()), Decimal(0))


    # if order_subtotal == 0 or order_paid == 0:
    #     return Decimal('0.00')

    # proportional_value = (Decimal(item.price)/ order_subtotoal) * order_paid
    # refund = proportional_value.quantize(Decimal('0.01'))

    # return min(refund, order_paid - refunded_so_far)

    



    # original_total = Decimal(order.original_total or 0)
    # amount_paid = Decimal(order.amount_paid or 0)
    # refunded_so_far = Decimal(order.refunded_amount or 0)

    # if original_total <= 0 or amount_paid <= 0:
    #     return Decimal('0.00')
    
    # paid_ratio = amount_paid / original_total

    # item_subtotal = Decimal(item.price) 

    # refund = (item_subtotal * paid_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # remaining_refundable = amount_paid - refunded_so_far
    # return max(Decimal('0.00'), min(refund, remaining_refundable))



# from decimal import Decimal, ROUND_HALF_UP

# def calculate_proportional_refund(order, item):
#     """
#     Calculate how much to refund for `item` based on what the customer actually paid.
#     - order.original_total = total before discounts
#     - order.amount_paid = amount actually paid (after discounts/vouchers)
#     - item.price = unit price (your DB stores unit price), so multiply by quantity
#     - order.refunded_amount = already refunded so far

#     Returns a Decimal (two decimal places).
#     """
#     original_total = Decimal(order.original_total or 0)
#     amount_paid = Decimal(order.amount_paid or 0)
#     refunded_so_far = Decimal(order.refunded_amount or 0)

#     if original_total <= 0 or amount_paid <= 0:
#         return Decimal("0.00")

#     # fraction of original the customer actually paid
#     paid_ratio = amount_paid / original_total

#     # item.price is unit price in your DB — get subtotal for the item
#     item_subtotal = Decimal(item.price) * Decimal(item.quantity)

#     # proportional refund (rounded to 2 decimals)
#     refund = (item_subtotal * paid_ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

#     # remaining refundable balance for the order
#     remaining_refundable = amount_paid - refunded_so_far
#     if remaining_refundable <= Decimal("0.00"):
#         return Decimal("0.00")

#     return min(refund, remaining_refundable)


# def calculate_strict_voucher_refund(order, affected_items):
#     """
#     Strict Rule:
#     If remaining_total < coupon_min_amount → revoke coupon.
#     Refund = amount_paid - remaining_total.
#     """

#     # Use original total if available to prevent rounding drift
#     order_total = Decimal(order.original_total or order.total or 0)

#     # Total value of affected items (cancelled or returned)
#     affected_total = sum(item.price for item in affected_items)
#     remaining_total = order_total - affected_total

#     # Default refund values
#     refund_amount = Decimal("0.00")
#     discount_revoked = False

#     # Apply rule only if coupon exists and has a threshold
#     if (
#         getattr(order, "coupon_code", None)
#         and getattr(order, "coupon_min_amount", Decimal("0.00")) > 0
#         and remaining_total < order.coupon_min_amount
#     ):
#         # Coupon revoked — remove discount advantage
#         refund_amount = (order.amount_paid or Decimal("0.00")) - remaining_total
#         discount_revoked = True
#     else:
#         # Normal refund (coupon still valid or no coupon)
#         refund_amount = affected_total
#         discount_revoked = False

#     refund_amount = max(refund_amount, Decimal("0.00"))
#     return refund_amount, discount_revoked, remaining_total



def calculate_strict_voucher_refund(order, affected_items):
    """
    Strict voucher refund logic.

    1. If remaining_total < coupon_min_amount → revoke coupon.
        → Refund = amount_paid - remaining_total
    2. Else → Refund proportional to actual paid share (after discount)
    """

    order_total = Decimal(order.original_total or order.total or 0)
    affected_total = sum(item.price for item in affected_items)
    remaining_total = order_total - affected_total
    coupon_discount = Decimal(order.coupon_discount or 0)
    coupon_min_amount = Decimal(order.coupon_min_amount or 0)
    amount_paid = Decimal(order.amount_paid or 0)
    coupon_code = order.coupon_code

    # Default flags
    refund_amount = Decimal("0.00")
    discount_revoked = False

    # Effective paid total after discount
    effective_total = order_total - coupon_discount

    # --- Case 1: Coupon revoked ---
    if coupon_code and coupon_min_amount > 0 and remaining_total < coupon_min_amount:
        refund_amount = amount_paid - remaining_total
        discount_revoked = True

    # --- Case 2: Coupon still valid or no coupon ---
    else:
        if coupon_discount > 0:
            # refund proportional to paid total (after discount)
            paid_ratio = affected_total / order_total
            refund_amount = (effective_total * paid_ratio).quantize(Decimal("0.01"))
        else:
            refund_amount = affected_total

    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"REFUND DEBUG → order_total={order.original_total}, affected_total={affected_total}, remaining_total={remaining_total}, coupon={order.coupon_code}, paid={order.amount_paid}, refund={refund_amount}, revoked={discount_revoked}")

    return refund_amount, discount_revoked, remaining_total