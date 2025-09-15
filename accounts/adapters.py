from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages
from allauth.exceptions import ImmediateHttpResponse

class CustomAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        """
        Redirect to home page after login
        """
        return reverse("home")

    def save_user(self, request, user, form, commit=True):
        """
        Save user for standard signup (email/password)
        """
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False  # require manual activation
        if commit:
            user.save()
        return user

    def is_open_for_signup(self, request):
        return True


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        """
        Populate full_name and activate social users
        """
        user = super().save_user(request, sociallogin, form)
        data = sociallogin.account.extra_data or {}

        # Set full_name reliably
        user.full_name = (
            data.get('name')
            or " ".join(n for n in [data.get('given_name'), data.get('family_name')] if n)
            or user.email.split('@')[0]
        )

        # Activate immediately
        user.is_active = True
        user.save()
        return user

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Prevent auto-signup if the account already exists
        """
        email = sociallogin.account.extra_data.get('email')
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return False
        return True

    # def pre_social_login(self, request, sociallogin):
    #     """
    #     Check for duplicate or unregistered accounts and show proper messages
    #     """
    #     email = sociallogin.account.extra_data.get('email')
    #     User = get_user_model()
    #     user_exists = User.objects.filter(email=email).exists()

    #     # Determine the view type
    #     view_name = request.resolver_match.view_name if request.resolver_match else ''

    #     # Trying to register an existing account
    #     if view_name == 'register' and user_exists:
    #         messages.error(request, "This account is already registered. Please login instead.")
    #         return redirect('register')

    #     # Trying to login with an unregistered account
    #     elif view_name == 'login' and not user_exists:
    #         messages.error(request, "This account is not registered. Please sign up first.")
    #         return redirect('login')

    def pre_social_login(self, request, sociallogin):
        """Prevent auto-signup and handle login/register cases"""
        email = sociallogin.account.extra_data.get('email')
        User = get_user_model()

        if not email:
            messages.error(request, "Google did not return an email.")
            raise ImmediateHttpResponse(redirect("login"))

        user_exists = User.objects.filter(email=email).exists()

        # If the user already exists → connect and log in
        if user_exists:
            existing_user = User.objects.get(email=email)
            sociallogin.connect(request, existing_user)
            return  

        # If the user does not exist → redirect to register
        messages.error(request, "This Google account is not registered. Please sign up first.")
        raise ImmediateHttpResponse(redirect("register"))