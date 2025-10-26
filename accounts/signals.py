# from allauth.account.signals import user_signed_up

# #receiver is a helper decorater to connects function to signals
# from django.dispatch import receiver

# @receiver(user_signed_up)
# def create_full_name(request, user, sociallogin=None, **kwargs):
#     """ 
#     This is to create full_name from googles data when a user
#     signs up via google.
#     """

#     if sociallogin and sociallogin.account.provider == 'google':
#         extra = sociallogin.account.extra_data or {}

#         user.full_name = (
#             extra.get('name')
#             or " ".join(n for n in [extra.get('given_name'), extra.get('family_name')] if n)
#             or user.email.split('@')[0]
#         )
#         user.is_active = True
#         user.save()


# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django.conf import settings

from .models import CustomUser, UserReferral, generate_referral_code
from wallet.models import Wallet


@receiver(post_save, sender=CustomUser)
def handle_user_referral(sender, instance, created, **kwargs):
    """
    Create referral record for new users.
    If referred_by is set, reward the referrer with ₹500.
    """
    if not created:
        return

    # Step 1: Ensure a referral record exists
    referral_record, created_ref = UserReferral.objects.get_or_create(user=instance)

    # Step 2: If user was referred by someone → reward referrer
    if referral_record.referred_by:
        referrer = referral_record.referred_by.user
        wallet, _ = Wallet.objects.get_or_create(user=referrer)

        wallet.balance += Decimal("500.00")
        wallet.save()

        print(f"Referral Bonus: {referrer} earned ₹500 for referring {instance}")
