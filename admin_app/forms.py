from django import forms
from .models import Coupon, Banner
from django.utils import timezone
from django.core.exceptions import ValidationError

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
        code = cleaned_data.get('code')

        if code:
            exists = Coupon.objects.filter(
                code__iexact=code
            ).exclude(id=self.instance.id).exists()

            if exists:
                self.add_error(
                    'code',
                    "A coupon with this code already exists."
                )

        # date Validation rules
        if valid_from and valid_from < timezone.now().date():
            raise forms.ValidationError("Start date cannot be in the past")

        if valid_from and valid_to and valid_to < valid_from:
            raise forms.ValidationError("End date cannot be before start date.")

        if valid_to and valid_to < timezone.now().date():
            raise forms.ValidationError("The coupon expiry date cannot be in the past.")

        # 2. Amount validations
        if discount_amount and discount_amount <= 0:
            raise forms.ValidationError("Discount amount must be greater than 0.")

        if minimum_amount and minimum_amount < 0:
            raise forms.ValidationError("Minimum amount cannot be negative.")

        if minimum_amount and discount_amount and discount_amount > minimum_amount:
            raise forms.ValidationError("Discount amount cannot exceeds minimum amount.")

        # Coupon code validation
        if code and " " in code:
            raise forms.ValidationError("Coupon code cannot contain spaces.")

        if code:
            cleaned_data['code'] = code.upper()
        
        return cleaned_data


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ['title', 'is_active', 'image']
