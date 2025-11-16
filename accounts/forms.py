from django.contrib.auth.forms import UserCreationForm
from allauth.socialaccount.forms import SignupForm
from .models import CustomUser,UserReferral
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import timezone


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    referrer_code = forms.CharField(required=False, max_length=8, label="referrer Code (optional)",
        widget=forms.TextInput(attrs={'placeholder': 'Enter referrer code if any'}))

    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'password1', 'password2', 'referrer_code']



    def clean_email(self):
        email = self.cleaned_data.get("email").strip().lower()

        try:
            user = CustomUser.objects.get(email=email)

            if not user.is_verified:
                # Let the view handle the resend + redirect
                self._unverified_user = user
                return email

            raise ValidationError("This email is already registered.")

        except CustomUser.DoesNotExist:
            return email

    def clean_referrer_code(self):
        code = self.cleaned_data.get('referrer_code')

        if code:
            code = code.strip().upper()
            if not UserReferral.objects.filter(referrer_code=code).exists():
                raise ValidationError("Invalid referrer code.")
        return code

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')

        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")
        
        validate_password(p1)

        return p2
        

class CustomSocialSignUpForm(SignupForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("The account is already registered. Please login instead.")
        
        return email

        

