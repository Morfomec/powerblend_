from .models import Coupon
from accounts.models import generate_referral_code
from decimal import Decimal 
from django.utils import timezone


def reward_referrer(referrer_user):
    code = generate_referral_code(prefix='REF')
    while Coupon.objects.filter(code=code).exists():
        code = generate_coupon_code(prefix='REF')

    coupon = Coupon.objects.create(code=code,
        owner=referrer_user,
        discount_type=Coupon.PERCENT,
        discount_value=Decimal('10.00'),
        max_uses=1,
        min_order_value=Decimal('500.00'),
        expires_at=timezone.now() + timezone.timedelta(days=30),
    )
    return coupon
