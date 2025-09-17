from django import forms 

class BasketAddForm(forms.Form):
    variant_id = forms.IntegerField()
    quantity = forms.IntegerField(min_value=1, initial=1)

