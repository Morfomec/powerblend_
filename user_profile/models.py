from django.db import models
from django.conf import settings

# Create your models here.

class Address(models.Model):
    ADDRESS_TYPES = (
        ('HOME', 'Home'),
        ('OFFICE', 'Office'),
        ('OTHER', 'Other'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    second_mobile = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="INDIA")
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES, default='HOME')
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_At = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        #only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.address_type}"