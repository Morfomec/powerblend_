from django.db import models
from django.conf import settings
from django.utils import timezone

from products.models import ProductVariant
import random, string
# Create your models here.


def generate_order_id():
    """
    helper function to create human readable order IDs Example: ORD-20250928-AB12
    """
    date = timezone.now().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{date}-{suffix}"

# order model
class Order(models.Model):
    STATUS_CHOICES= [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
        ('wallet', 'Wallet'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    order_id = models.CharField(max_length=32, unique=True, default=generate_order_id, editable=False)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='None')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"{self.order_id} ({self.user})"


    #to re calculate total from OrderItems

    def recalc_total(self):
        total = sum([
            item.item_total for item in self.items.filter(is_cancelled=False, is_returned=False)
            # for item in self.items.filter(status__in=['pending', 'confirmed', 'shipped', 'delivered'])
        ])

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


# OrderItems Model , links each order to a ProductVariant
class OrderItem(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
        ('out_for_delivery', 'Out for delivery'),
        ('partially_cancelled', 'Partially Cancelled'),
    ]

    RETURN_CHOICES = [
        ('none', 'None'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=20, decimal_places=2)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    #cancellation fields
    is_cancelled = models.BooleanField(default=False)
    cancelled_reason = models.TextField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)


    # returns fields
    is_returned = models.BooleanField(default=False)
    returned_reason = models.TextField(blank=True, null=True)
    returned_at = models.DateTimeField(blank=True, null=True)
    return_status = models.CharField(max_length=20, choices=RETURN_CHOICES, default='none')

    @property
    def item_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.variant} x {self.quantity} ({self.order.order_id})"