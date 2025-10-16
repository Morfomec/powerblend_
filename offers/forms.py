from django import forms
from .models import Offer

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        # fields = ['name', 'description', 'offer_type', 'discount_percent', 'categories', 'products', 'start_date', 'end_date', 'active']
        fields = '__all__'
