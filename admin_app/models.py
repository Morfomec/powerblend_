from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

# Create your models here.

# class AdminProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     profile_image = models.ImageField(upload_to='admin_profile_images/', default='default.png')
#     full_name


class Coupon(models.Model):

    
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateField()
    valid_to = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_to

    def __str__(self):
        return self.code


class UserCoupon(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('user', 'coupon')

        


# Banners

class Banner(models.Model):
    title = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to='images/banners/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title or 'Banner'
    

