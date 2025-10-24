from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.conf import Settings
# Create your models here.



class Coupon(models.Model):

    DISCOUNT_TYPE_CHOICES = [
        ('pericent', 'Percent'),
        ('fixed', 'Fixed'),
    ]

    # code = models.CharField(max_length=50,)