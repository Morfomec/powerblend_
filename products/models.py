from django.db import models
from category.models import Category
from utils.file_uploads import product_image_upload_path
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import F, Value

from offers.utils import get_discount_info_for_variant
# Create your models here.

class Product(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    max_quantity_per_order = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True)


    def __str__(self):
        return self.name

    class Meta:
        db_table = 'products'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            #to ensure slug is unique
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        




#to add multiple images
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_upload_path)
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} - Image"

    class Meta:
        db_table = 'products_image'

class Flavor(models.Model):
    flavor = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.flavor

class Weight(models.Model):
    weight = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.weight


# for product variants
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    flavor = models.ForeignKey(Flavor, on_delete=models.SET_NULL, blank=True, null=True)
    weight = models.ForeignKey(Weight, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_listed = models.BooleanField(default=True)
    max_quantity_per_order = models.PositiveIntegerField(default=5)
    

    # def clean(self):
    # # Skip validation if using F() expressions (database will handle it)
    #     if isinstance(self.stock, F):
    #         return

    #     # Only check when actual integer value is known
    #     if self.stock is not None and self.stock < 0:
    #         raise ValidationError({"stock": "Stock cannot be negative"})

    # def save(self, *args, **kwargs):
    #     self.full_clean()  # calls clean()
    #     super().save(*args, **kwargs)
    
    # @property
    # def original_price(self):
    #     return self.price + 950

    # @property
    # def save_price(self):
    #     return self.original_price - self.price

    from offers.models import Offer


    @property
    def active_offer(self):
        return get_discount_info_for_variant(self)

    # @property
    # def discounted_price(self):
    #     if self.active_offer:
    #         return self.active_offer.discount_amount(self.price)
    #     return self.price
    

    @property
    def discounted_price(self):
        offer = self.active_offer
        if offer and 'final_price' in offer:
            return offer['final_price']
        return self.price


    @property
    def savings(self):
        offer = self.active_offer
        if offer and 'savings' in offer:
            return offer['savings']
        return 0

    @property
    def discount_percentage(self):
        offer = self.active_offer
        if offer and 'discount_percent' in offer:
            return offer['discount_percent']
        return 0

    # @property
    # def savings(self):
    #     if self.active_offer:
    #         return self.active_offer.savings(self.price)
    #     return 0

    
    # @property
    # def discount_percentage(self):
    #     if self.original_price > 0:
    #         return round(((self.original_price - self.price)/ self.original_price) * 100, 2)
    #     return 0

    def __str__(self):
        details = []
        if self.flavor:
            details.append(self.flavor)
        if self.weight:
            details.append(self.weight)
        return f"{self.product.name} - {'/'.join(str(d) for d in details)}"

    class Meta:
        db_table = "product_variants"
        unique_together = ('product', 'flavor', 'weight')
        constraints = [ models.CheckConstraint(check=models.Q(stock__gte=0), name='stock_non_negative')]