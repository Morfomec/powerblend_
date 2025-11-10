from django.db.models import F
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

# Increment stock(when cancelling or returning)


def increment_stock(variant, qty):
    variant.stock = F('stock') + qty
    variant.save(update_fields=['stock'])
    variant.refresh_from_db()


# decrement stock when placing an order
def decrement_stock(variant, qty):
    variant.stock = F('stock') - qty
    variant.save(update_fields=['stock'])


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
            refund_amount = (
                effective_total *
                paid_ratio).quantize(
                Decimal("0.01"))
        else:
            refund_amount = affected_total

    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        f"REFUND DEBUG → order_total={
            order.original_total}, affected_total={affected_total}, remaining_total={remaining_total}, coupon={
            order.coupon_code}, paid={
                order.amount_paid}, refund={refund_amount}, revoked={discount_revoked}")

    return refund_amount, discount_revoked, remaining_total
