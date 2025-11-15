from django import forms
from .models import Offer
from django.core.exceptions import ValidationError
import re
from django.utils import timezone
import datetime

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = '__all__'

    widgets = {
        'name': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter offer name'
        }),
        'offer_type': forms.Select(attrs={
            'class': 'form-control',
        }),
        'description': forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Write offer description...',
            'rows': 3
        }),
        'discount_percent': forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00'
        }),
        'start_date': forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}
        ),
        'end_date': forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}
        ),
        'active': forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    }


    def clean(self):
        cleaned_data = super().clean()

        name = cleaned_data.get('name', '').strip().lower()
        offer_type = cleaned_data.get('offer_type')
        discount_percent = cleaned_data.get('discount_percent')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')


        if not name: 
            raise forms.ValidationError("Offer name cannot be empty.")

        duplicate = Offer.objects.filter(name__iexact=name, offer_type=offer_type)

        if self.instance.id:
            duplicate = duplicate.exclude(id=self.instance.id)


        if duplicate.exists():
            raise forms.ValidationError(
                f"An offer name '{name}' already exists for this type of offer."
            )

        if not re.match(r"^[A-Za-z0-9\s\-_.]+$", name):
            raise forms.ValidationError("Offer name contains invalid characters.")

        cleaned_data['name'] = name


        if discount_percent is None:
            raise forms.ValidationError("Discount percentage is required.")

        if discount_percent <= 0:
            raise forms.ValidationError("Discount cannot below 1%.")
        
        if discount_percent > 90:
            raise forms.ValidationError("Maximum allowed discount is 90%.")

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be earlier than start date.")

            # Only validate past date for NEW offers
            if not self.instance.id:
                # Convert datetime → date before comparison
                start_date_as_date = start_date.date() if isinstance(start_date, datetime.datetime) else start_date

                if start_date_as_date < timezone.now().date():
                    raise forms.ValidationError("Start date cannot be in the past.")
        else:
            if start_date or end_date:
                raise forms.ValidationError("Both start and end date are required.")

        if offer_type == "product":
            if not self.data.getlist("products"):
                raise forms.ValidationError("Please select at least one product for a product offer.")

        if offer_type == "category":
            if not self.data.getlist("categories"):
                raise forms.ValidationError("Please select at least one category for a category offer.")

        
        return cleaned_data