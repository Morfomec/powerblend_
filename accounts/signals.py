# accounts/signals.py
from django.db.models.signals import post_save
from decimal import Decimal
from django.conf import settings
from wallet.models import Wallet

from allauth.socialaccount.signals import pre_social_login, social_account_added
from django.dispatch import receiver
from allauth.socialaccount.models import SocialAccount
from .models import CustomUser, UserReferral, generate_referral_code


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





# @receiver(pre_social_login)
# def populate_user_from_google(sender, request, sociallogin, **kwargs):
#     """
#     Populate CustomUser data from Google account before login.
#     Runs before the user is actually logged in or saved.
#     """
#     user = sociallogin.user

#     if sociallogin.account.provider == 'google':
#         data = sociallogin.account.extra_data

#         # Extract name data from Google
#         full_name = data.get('name')
#         first_name = data.get('given_name', '')
#         last_name = data.get('family_name', '')

#         # Prefer full name, or construct from parts
#         if full_name:
#             user.full_name = full_name
#         elif first_name or last_name:
#             user.full_name = f"{first_name} {last_name}".strip()
#         else:
#             # fallback from email if Google provides no name
#             user.full_name = user.email.split('@')[0].replace('.', ' ').title()

#         # Set profile image if available
#         if data.get('picture'):
#             user.profile_image = data.get('picture')

#         # Ensure email field is populated (Google should always provide it)
#         if not user.email and data.get('email'):
#             user.email = data['email']



# @receiver(social_account_added)
# def create_referral_on_social_signup(sender, request, sociallogin, **kwargs):
#     user = sociallogin.user

#     if not user.pk:  # not saved yet
#         user.save()  # force save if not persisted

#     UserReferral.objects.get_or_create(
#         user=user,
#         defaults={'referral_code': generate_referral_code()}
#     )



# @receiver(post_save, sender=CustomUser)
# def handle_user_referral(sender, instance, created, **kwargs):
#     """
#     Create referral record for new users.
#     If referred_by is set, reward the referrer with ₹500.
#     """
#     if not created:
#         return

#     # Step 1: Ensure a referral record exists
#     referral_record, created_ref = UserReferral.objects.get_or_create(user=instance)

#     # Step 2: If user was referred by someone → reward referrer
#     if referral_record.referred_by:
#         referrer = referral_record.referred_by.user
#         wallet, _ = Wallet.objects.get_or_create(user=referrer)

#         wallet.balance += Decimal("500.00")
#         wallet.save()

#         print(f"Referral Bonus: {referrer} earned ₹500 for referring {instance}")
