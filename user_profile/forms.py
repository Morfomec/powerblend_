from django import forms
from .models import Address
from django.conf import settings
from django.contrib.auth import get_user_model
from phonenumber_field.formfields import PhoneNumberField
# from phonenumber_field.widgets import PhoneNumberPrefixWidget

import re


User = get_user_model()

# Prevent repetitive pincodes like 000000, 111111, etc.
INVALID_PINCODES = {f"{d}{d}{d}{d}{d}{d}" for d in "0123456789"}


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'profile_image', 'email', 'mobile', 'date_of_birth', 'gender', 'country']

class EmailChangeForm(forms.Form):
    new_email = forms.EmailField()



class AddressForm(forms.ModelForm):
    mobile = PhoneNumberField(region="IN",
        # widget=PhoneNumberPrefixWidget(region="IN")
    )
    second_mobile = PhoneNumberField(region="IN", required=False,
        # widget=PhoneNumberPrefixWidget(region="IN")
    )

    class Meta:
        model = Address
        fields = ['full_name', 'mobile', 'second_mobile', 'address', 'city', 'state', 'postal_code', 'country', 'address_type', 'is_default']

    def clean_full_name(self):
        name = self.cleaned_data.get("full_name", "").strip()

        if not name:
            raise forms.ValidationError("Full name cannot be blank.")

        if not re.match(r"^[A-Za-z][A-Za-z\s\.\-']+$", name):
            raise forms.ValidationError("Full name should contain letters.")

        return re.sub(r"\s+", " ", name)

    
    def clean_postal_code(self):
        postal = (self.cleaned_data.get("postal_code")or "").strip()

        if not postal.isdigit() or len(postal) != 6:
            raise forms.ValidationError("Postal code must be exactly 6 digits.")
        if postal in INVALID_PINCODES:
            raise forms.ValidationError("Invalid postal code pattern (e.g., 000000, 111111, etc.)")

        return postal

    def clean_address(self):
        addr = (self.cleaned_data.get("address") or"").strip()

        if len(addr) < 10:
            raise forms.ValidationError("Address is too short. Please provide more details.")
        
        return addr

    #cross-field calidations

    def clean(self):
        cleaned = super().clean()
        mobile = cleaned.get("mobile")
        second_mobile = cleaned.get("second_mobile")

        if second_mobile and mobile and mobile == second_mobile:
            raise forms.ValidationError("Primary and secondary mobile numbers cannot be the same.")

            return cleaned


class verifyOTPForm(forms.ModelForm):
    otp = forms.CharField(max_length=6, label='Enter OTP')