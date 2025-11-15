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
    profile_image = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['full_name', 'profile_image', 'mobile', 'date_of_birth', 'gender', 'country']

class EmailChangeForm(forms.Form):
    new_email = forms.EmailField()



class AddressForm(forms.ModelForm):
    mobile = PhoneNumberField(region="IN")
    second_mobile = PhoneNumberField(region="IN", required=False)

    class Meta:
        model = Address
        fields = ['full_name', 'mobile', 'second_mobile', 'address', 'city', 'state', 'postal_code', 'country', 'address_type', 'is_default']

    def clean_full_name(self):
        name = self.cleaned_data.get("full_name", "").strip()

        if not name:
            raise forms.ValidationError("Full name cannot be blank.")

        if re.search(r"[^\w\s\.\-']", name):
            raise forms.ValidationError("Full name contains invalid characters.")

        if re.fullmatch(r"[.\-\/\\]+", name):
            raise forms.ValidationError("Full name should contain letters.")

        if len(re.findall(r"[A-Za-z]", name)) < 2:
            raise forms.ValidationError("Full name must contain alphabetic characters.")

        return re.sub(r"\s+", " ", name)

    def clean_address(self):
        addr = (self.cleaned_data.get("address") or "").strip()

        if len(addr) < 10:
            raise forms.ValidationError("Provide a more detailed address.")

        if re.fullmatch(r"[^\w\s]+", addr):
            raise forms.ValidationError("Address cannot contain only special characters.")

        if re.search(r"[^\w\s]{4,}", addr):
            raise forms.ValidationError("Address contains too many special characters.")

        if not re.match(r"^[A-Za-z0-9\s,.\-/#]+$", addr):
            raise forms.ValidationError("Address contains invalid characters.")

        return addr

    def clean_city(self):
        city = (self.cleaned_data.get("city") or "").strip()

        if not re.match(r"^[A-Za-z\s\-]+$", city):
            raise forms.ValidationError("City must contain only letters.")

        return city

    def clean_state(self):
        state = (self.cleaned_data.get("state") or "").strip()

        if not re.match(r"^[A-Za-z\s\-]+$", state):
            raise forms.ValidationError("State must contain only letters.")

        return state

    def clean_postal_code(self):
        postal = (self.cleaned_data.get("postal_code") or "").strip()

        if not postal.isdigit() or len(postal) != 6:
            raise forms.ValidationError("Postal code must be exactly 6 digits.")

        if postal.startswith("0"):
            raise forms.ValidationError("Postal code cannot start with 0.")

        if postal in INVALID_PINCODES:
            raise forms.ValidationError("Invalid postal code pattern (111111, 000000, etc.).")

        return postal

    def clean(self):
        cleaned = super().clean()
        mobile = cleaned.get("mobile")
        second_mobile = cleaned.get("second_mobile")

        if second_mobile and mobile and mobile == second_mobile:
            raise forms.ValidationError("Primary and secondary mobile cannot be the same.")

        # Block invalid characters in phone numbers
        if mobile and not str(mobile).replace("+", "").isdigit():
            raise forms.ValidationError("Invalid characters in mobile number.")

        return cleaned


class verifyOTPForm(forms.ModelForm):
    otp = forms.CharField(max_length=6, label='Enter OTP')