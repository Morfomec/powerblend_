from django.db import models
from django.utils.text import slugify

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="subcategories") #self is to link a category to another category
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    promo_image = models.ImageField( upload_to = 'featured_promo/', blank=True, null=True)

    # discount_percentage = models.PositiveIntegerField(default=0)
    discount = models.DecimalField(default=0,max_digits=5, decimal_places=2, blank=True, null=True, help_text = "Discount (eg: 10.50 for 10.5%)")

    #for readability

    def save(self, *args, **kwargs):
        if not self.slug:
            if self.name:
                base_slug = slugify(self.name)
                self.slug = base_slug
                counter = 1
                while Category.objects.filter(slug=self.slug).exists():
                    self.slug = f"{base_slug} - {counter}"
                    counter += 1
            else:
                self.slug = "category"
        super().save(*args, **kwargs)

    #changes how it display in the admin side-bar
    class Meta:
        verbose_name_plural = "Categories"
        db_table = 'categories'

    #change how it displayed in the shell (to get more precise  name)
    def __str__(self):
        return self.name



