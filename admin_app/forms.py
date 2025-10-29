from django import forms
from .models import Coupon
from django.utils import timezone


class ApplyCouponForm(forms.Form):
    code = forms.CharField(max_length=50, label='Coupon Code')

    
class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_amount', 'minimum_amount', 'valid_from', 'valid_to', 'is_active']

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount_amount = cleaned_data.get('discount_amount')
        minimum_amount = cleaned_data.get('minimum_amount')

        # Validation rules
        if valid_from and valid_to and valid_to < valid_from:
            raise forms.ValidationError("End date cannot be before start date.")

        if valid_to and valid_to < timezone.now().date():
            raise forms.ValidationError("The coupon expiry date cannot be in the past.")

        # 2. Amount validations
        if discount_amount and discount_amount <= 0:
            raise forms.ValidationError("Discount amount must be greater than 0.")

        if minimum_amount and minimum_amount < 0:
            raise forms.ValidationError("Minimum amount cannot be negative.")

        return cleaned_data