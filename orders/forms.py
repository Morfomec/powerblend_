from django import forms
from .models import Order




class CancelOrderForm(forms.Form):
    reason = forms.CharField(required=False)

class CancelItemForm(forms.Form):
    item_id = forms.IntegerField()
    reason = forms.CharField(required=False)

class ReturnItemForm(forms.Form):
    item_id = forms.IntegerField()
    reason = forms.CharField(required=True)

class ReturnOrderForm(forms.Form):
    reason = forms.CharField(required=True)





class AdminOrderStatusForm(forms.Form):

    status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3}))


    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('status')
        reason = cleaned.get('reason', '').strip()


        #require reason for cancellation or order return
        if status in ['cancelled', 'returned'] and not reason:
            raise forms.ValidationError("Please provide reason for cancelling or returning the order.")
        return cleaned