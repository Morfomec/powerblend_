from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'mobile', 'second_mobile', 'address', 'city', 'state', 'postal_code', 'country', 'address_type', 'is_default']