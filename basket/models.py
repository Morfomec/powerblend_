from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant
# Create your models here.

class Basket(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="basket")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return  f"Basket of {self.user.full_name if self.user else "Guest"}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

class BasketItem(models.Model):
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # to track the item came from wishlist or not
    from_wishlist = models.BooleanField(default=False)

    @property
    def price(self):
        return self.variant.price
        
    @property
    def subtotal(self):
        from offers.utils import get_discount_info_for_variant
        discount_info = get_discount_info_for_variant(self.variant)
        return discount_info['price'] * self.quantity
    
    def __str__(Self):
        return f"{self.variant} x {self.quantity}"
    

