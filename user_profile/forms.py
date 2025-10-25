from django import forms
from .models import Address
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'profile_image', 'email', 'mobile', 'date_of_birth', 'gender', 'country']

class EmailChangeForm(forms.Form):
    new_email = forms.EmailField()


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'mobile', 'second_mobile', 'address', 'city', 'state', 'postal_code', 'country', 'address_type', 'is_default']

class verifyOTPForm(forms.ModelForm):
    otp = forms.CharField(max_length=6, label='Enter OTP')