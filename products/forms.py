from django import forms
from .models import Product, ProductImage, ProductVariant, Flavor, Weight
from category.models import Category

class ProductForm(forms.ModelForm):
   
    class Meta:
        model = Product
        fields = ["name", "category", "description", "is_listed"]
    


    def clean_name(self):
        raw_name = (self.cleaned_data.get("name") or "").strip()
        name = " ".join(raw_name.split())  # normalize multiple spaces

        # Exclude the product in update mode
        qs = Category.objects.filter(name__iexact=name)

        if qs.exists():
            raise forms.ValidationError(
                "Product name cannot be exactly the same as an existing category name."
            )

        return name


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            # Make flavor and weight readonly but STILL submitted
            self.fields['flavor'].widget.attrs['readonly'] = True
            self.fields['weight'].widget.attrs['readonly'] = True

            # Also visually lock it
            self.fields['flavor'].widget.attrs['style'] = "pointer-events: none; background:#f1f1f1;"
            self.fields['weight'].widget.attrs['style'] = "pointer-events: none; background:#f1f1f1;"
        
class FlavorForm(forms.ModelForm):
    class Meta:
        model = Flavor
        fields = ["flavor"]
    
class WeightForm(forms.ModelForm):
    class Meta:
        model = Weight
        fields = ["weight"]

