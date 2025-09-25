from django.db import models
from django.conf import settings
from products.models import ProductVariant
from django.utils import timezone


# Create your models here.

class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Wishlist of {self.user.username}"
    
    class Meta:
        db_table = 'wishlist'

    @property
    def total_items(self):
        return self.items.count()

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("wishlist", "variant")
        db_table = 'wishlistitem'

    def __str__(self):
        return f"{self.variant} in {self.wishlist.user.full_name}'s wishlist"