from django.db import models

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="subcategories") #self is to link a category to another category
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # discount_percentage = models.PositiveIntegerField(default=0)
    discount = models.DecimalField(default=0,max_digits=5, decimal_places=2, blank=True, null=True, help_text = "Discount (eg: 10.50 for 10.5%)")

    #for readability

    #changes how it display in the admin side-bar
    class Meta:
        verbose_name_plural = "Categories"
        db_table = 'categories'

    #change how it displayed in the shell (to get more precise  name)
    def __str__(self):
        return self.name



