from django.db import models
from django.conf import settings
from products.models import Product
from orders.models import OrderItem

# Create your models here.

class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        db_table = 'product_reviews'

    def __str__(self):
        return f"{self.product.name} - {self.rating}-stars by {self.user.full_name}"