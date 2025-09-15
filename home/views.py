from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from products.models import Product
from category.models import Category

# Create your views here.



# @never_cache
# @login_required(login_url='login')
def home_view(request):
    products = Product.objects.all().filter(is_listed=True)

    context = {
        'products': products,
    }
    return render(request, "home.html", context)



def list_products(request):
    """
    return products list page
    """

    products = Product.objects.filter(is_listed=True)
    categories = Category.objects.all()

    # search
    search_query = request.GET.get("search")
    
    if search_query:
        products = products.filter(name__icontains=search_query) | products.filter(description__icontains=search_query)

    # filter by category

    category_id = request.GET.get("category")

    if category_id:
        products=products.filter(category_id=category_id)


    #filter by price

    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    
    #sorting

    sort_option = request.GET.get("sort")
    if sort_option == "price_low":
        products = products.order_by("price")
    elif sort_option == "price_high":
        products = products.order_by("-price")
    elif sort_option == "az":
        products = products.order_by("name")
    elif sort_option == "za":
        products = products.order_by("-name")
    elif sort_option == "new":
        products = products.order_by("-created_at")
    elif sort_option == "featured":
        products = products.filter(is_featured=True)

    context = {
        'products': products,
    }
    return render(request, "product_listing.html", context)





def detail_product(request, id):
    """
    return a single product detail page
    """
    try:
        single_product = get_object_or_404(Product, id=id, is_listed=True)
    except Exception as e:
        raise e
        
    context = {
        "product" : single_product,
    }
    return render(request, "product_detail.html", context)