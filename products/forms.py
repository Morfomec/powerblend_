from django import forms
from .models import Product, ProductImage, ProductVariant, Flavor, Weight

class ProductForm(forms.ModelForm):
   
    class Meta:
        model = Product
        fields = ["name", "category", "description", "is_listed"]
    




class ProductVariantForm(forms.ModelForm):
    flavor = forms.ModelChoiceField(
        queryset = Flavor.objects.all(),
        required = False,
        empty_label = "Select Flavor"
    )

    weight = forms.ModelChoiceField(
        queryset = Weight.objects.all(),
        required = False,
        empty_label = "Select Weight/Size"
    )

    class Meta:
        model = ProductVariant
        fields = ["flavor", "weight", "price", "stock"]
 
        
class FlavorForm(forms.ModelForm):
    class Meta:
        model = Flavor
        fields = ["flavor"]
    
class WeightForm(forms.ModelForm):
    class Meta:
        model = Weight
        fields = ["weight"]

