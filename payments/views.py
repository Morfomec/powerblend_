from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages




# Create your views here.

def checkout_view(request):
    return render(request, 'checkout.html')

