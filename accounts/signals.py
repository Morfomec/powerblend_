from allauth.account.signals import user_signed_up

#receiver is a helper decorater to connects function to signals
from django.dispatch import receiver

@receiver(user_signed_up)
def create_full_name(request, user, sociallogin=None, **kwargs):
    """ 
    This is to create full_name from googles data when a user
    signs up via google.
    """

    if sociallogin and sociallogin.account.provider == 'google':
        extra = sociallogin.account.extra_data or {}

        user.full_name = (
            extra.get('name')
            or " ".join(n for n in [extra.get('given_name'), extra.get('family_name')] if n)
            or user.email.split('@')[0]
        )
        user.save()