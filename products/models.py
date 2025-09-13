from django.db import models
from category.models import Category
from utils.file_uploads import product_image_upload_path

# Create your models here.

class Product(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    stock = models.PositiveIntegerField(blank=True, null=True)
    is_listed = models.BooleanField(default=True)


    def __str__(self):
        return self.name

    class Meta:
        db_table = 'products'
        




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