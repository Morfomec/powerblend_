from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from products.models import ProductVariant
import random
import string
# Create your models here.


def generate_order_id():
    """
    helper function to create human readable order IDs Example: ORD-20250928-AB12
    """
    date = timezone.now().strftime("%Y%m%d")
    suffix = ''.join(
        random.choices(
            string.ascii_uppercase +
            string.digits,
            k=4))
    return f"ORD-{date}-{suffix}"

# order model


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('return_requested', 'Return Requested'),
        ('partially_cancelled', 'Partially cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
        ('wallet', 'Wallet'),
    ]

    RETURN_CHOICES = [
        ('pending', 'Pending'),
        ('return_requested', 'Return Requested'),
        ('return_approved', 'Return Approved'),
        ('return_rejected', 'Return Rejected'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders")
    order_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_order_id,
        editable=False)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        blank=True,
        null=True)
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending')

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    original_total = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.TextField(blank=True, null=True)
    is_refunded = models.BooleanField(default=False)

    is_returned = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True, null=True)
    return_at = models.DateTimeField(blank=True, null=True)
    return_status = models.CharField(
        max_length=50,
        choices=RETURN_CHOICES,
        default='pending')

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending')
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(
        max_length=255, blank=True, null=True)

    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    coupon_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_min_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True)
    refunded_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        """
        Override the default save() method to preserve the original total amount of the order
        """
        if not self.original_total and self.total:
            self.original_total = self.total
        super().save(*args, **kwargs)

    @property
    def final_amount(self):
        return self.total - self.discount_amount

    def __str__(self):
        return f"{self.order_id} ({self.user})"

    # to re calculate total from OrderItems

    def recalc_total(self):
        total = sum([item.item_total for item in self.items.filter(
            is_cancelled=False, is_returned=False)])

        self.total = total
        self.save(update_fields=['total'])

    def marks_items_delivered(self):
        """
        to mark all active items as delivered and updates order status
        """

        active_items = self.items.filter(is_cancelled=False, is_returned=False)

        for item in active_items:
            item.status = 'delivered'
            item.save(update_fields=['status'])

        self.update_status()

    def update_status(self):

        items = self.items.all()

        if all(item.is_cancelled or item.is_returned for item in items):
            self.status = 'cancelled'
        elif all(item.status == 'delivered' for item in items if not item.is_cancelled and not item.is_returned):
            self.status = 'delivered'
        elif any(item.is_cancelled or item.is_returned for item in items):
            self.status = 'partially_cancelled'
        else:
            self.status = 'pending'
        self.save(update_fields=['status'])

    def update_return_status(self):

        status = self.items.values_list('return_status', flat=True)
        if all(s == 'return_approved' for s in status):
            self.return_status = 'return_approved'
            self.is_returned = True

        elif all(s == 'return_requested' for s in status):
            self.return_status = 'return_requested'
        elif all(s == 'return_rejected' for s in status):
            self.return_status = 'return_rejected'
        elif all(s == 'returned' for s in status):
            self.return_status = 'returned'
        else:
            self.return_status = 'returned'
        self.save()

    def update_order_status(self):
        """
        Sync order status based on all its item statuses.
        """
        item_statuses = list(self.items.values_list('status', flat=True))

        if all(s == 'delivered' for s in item_statuses):
            self.status = 'delivered'

        elif all(s == 'cancelled' for s in item_statuses):
            self.status = 'cancelled'

        elif any(s in ['shipped', 'out_for_delivery'] for s in item_statuses):
            self.status = 'out_for_delivery' if 'out_for_delivery' in item_statuses else 'shipped'

        elif any(s == 'confirmed' for s in item_statuses):
            self.status = 'confirmed'

        elif any(s in ['cancelled', 'returned'] for s in item_statuses):
            self.status = 'partially_cancelled'

        else:
            self.status = 'pending'

        self.save(update_fields=['status'])

    def force_discount_reset_if_empty(self):
        active_items = self.items.filter(is_cancelled=False, is_returned=False)

        if not active_items.exists():
            # No items remaining → remove discount + prevent negative totals
            self.discount_amount = Decimal('0')
            self.coupon_discount = Decimal('0')
            self.coupon_code = None
            self.coupon_min_amount = Decimal('0')
            self.total = Decimal('0')
            self.save(update_fields=[
                'discount_amount', 'coupon_discount',
                'coupon_code', 'coupon_min_amount', 'total'
            ])


# OrderItems Model , links each order to a ProductVariant
class OrderItem(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('return_requested', 'Return Requested'),
        ('out_for_delivery', 'Out for delivery'),
        ('partially_cancelled', 'Partially Cancelled'),
    ]

    RETURN_CHOICES = [
        ('pending', 'Pending'),
        ('return_requested', 'Return Requested'),
        ('return_approved', 'Return Approved'),
        ('return_rejected', 'Return Rejected'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items')
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orderitems')

    # snapshot fields to remain things even if the product price or anything get deleted
    product_name = models.CharField(max_length=255)
    flavor_name = models.CharField(max_length=255, null=True, blank=True)
    weight_label = models.CharField(max_length=255, null=True, blank=True)

    # product_image = models.ImageField(upload_to='order_items/', null=True, blank=True)

    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=20, decimal_places=2)
    # price = models.DecimalField(max_digits=20, decimal_places=2)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending')

    # cancellation fields
    is_cancelled = models.BooleanField(default=False)
    cancelled_reason = models.TextField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    # returns fields
    is_returned = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)

    return_reason = models.TextField(blank=True, null=True)
    return_at = models.DateTimeField(blank=True, null=True)
    return_status = models.CharField(
        max_length=20,
        choices=RETURN_CHOICES,
        default='pending')

    @property
    def item_total(self):
        return self.price_at_purchase

    def __str__(self):
        return f"{self.variant} x {self.quantity} ({self.order.order_id})"

    @property
    def variant_total(self):
        return self.price_at_purchase

    @property
    def unit_price(self):
        return self.price_at_purchase / self.quantity

    @property
    def price(self):
        """
        Safety trap: prevents accidental use of old field 'price'.
        """
        raise AttributeError(
            "OrderItem.price no longer exists. Use `price_at_purchase` instead."
        )

    