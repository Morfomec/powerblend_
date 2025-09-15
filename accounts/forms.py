from django.contrib.auth.forms import UserCreationForm
from allauth.socialaccount.forms import SignupForm
from .models import CustomUser
from django import forms


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)


    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'password1', 'password2']

    #cutome validator for unique emails
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered!")
        return email
        

class CustomSocialSignUpForm(SignupForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("The account is already registered. Please login instead.")
        
        return email

class CustomSocialSignUpForm(SignupForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("The account is already registered. Please login instead.")
        
        return email

        