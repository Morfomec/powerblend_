from django.db import models
from django.config import settings
from django.utils import timezone

from products.models import ProductVariant
import random, string
# Create your models here.


def generate_order_id():
    """
    helper function to create human readable order IDs Example: ORD-20250928-AB12
    """
    date = timezone.now().strftime("%Y%m%d")