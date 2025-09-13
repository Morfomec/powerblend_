from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache

# Create your views here.



# @never_cache
# @login_required(login_url='login')
def home_view(request):
    return render(request, "home.html")

def list_products(request):
    """
    return products list page
    """

    return render(request, "products.html")

def detail_product(request):
    return render(request, "products_detail.html")