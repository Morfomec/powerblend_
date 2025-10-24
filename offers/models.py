from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from category.models import Category


# Create your models here.


class Offer(models.Model):
    from products.models import Product
    OFFER_CHOICES = (
        ('category', 'Category Offer'),
        ('product' , 'Product Offer'),
        ('referral' , 'Referral Offer'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    offer_type = models.CharField(max_length=20, choices=OFFER_CHOICES)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, help_text="Enter discount in percentage (e.g, 10 for 10%)")
    
    categories = models.ManyToManyField(Category, blank=True, related_name='offers')
    products = models.ManyToManyField(Product, blank=True, related_name='offers')

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Offer'
        verbose_name_plural = 'Offers'

    # def save(self, *args, **kwargs):
    #     if self.name:
    #         self.name = self.name.strip().lower()
    #     super().save(*Args, **kwargs)

    def __str__(self):
        return f"{self.name.title()} ({self.get_offer_type_display()}) - {self.discount_percent}%"

    
    # for Validation
    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError('End date must be after the date.')
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValidationError('Discount must be between 0 and 100.')


    def is_valid(self):
        now = timezone.noadmin_offer_listw()
        return self.active and (self.start_date <= now <= (self.end_date or now))

    # def discount_amount(self, price):
    #     if not self.is_valid():
    #         return (price * (self.discount_percent/100))


    @property
    def discount_amount(self, price):
        if not self.is_valid():
            return price
        discount = self.discount_percent / Deciaml(100)
        discounted_price = price * (1 - discount)
        return discounted_price

    @property
    def savings(self, price):
        if not self.is_valid():
            return Decimal(0)
        discount = self.discount_percent / Decimal(100)
        save_amount = price * save_amount
        return save_amount

    @property
    def original_price(self, price):
        if not self.is_valid():
            return price
        return price