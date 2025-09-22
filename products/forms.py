from django import forms
from .models import Product, ProductImage, ProductVariant, Flavor, Weight

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "description", "is_listed"]
        # widgets = {
        #     "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter product name"}),
        #     "category": forms.Select(attrs={"class": "form-select"}),
        #     "price": forms.NumberInput(attrs={"class": "form-control"}),
        #     "stock": forms.NumberInput(attrs={"class": "form-control"}),
        #     "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        #     "is_listed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        # }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "caption", "is_primary"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "caption": forms.TextInput(attrs={"class": "form-control", "placeholder": "Image caption"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

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

