from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from products.models import Product, ProductVariant
from category.models import Category
from wishlist.models import Wishlist, WishlistItem

# Create your views here.



# @never_cache
# @login_required(login_url='login')
def home_view(request):
    products = Product.objects.filter(is_listed=True).prefetch_related("variants")
    # variant = ProductVariant.objects.all()

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_variant_ids = wishlist.items.values_list('variant_id', flat=True)


    context = {
        'products': products,
        'wishlist_variant_ids': list(wishlist_variant_ids),
    }
    return render(request, "home.html", context)



def list_products(request):
    """
    return products list page
    """

    products = Product.objects.filter(is_listed=True).prefetch_related("variants")
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


    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = getattr(request.user, 'wishlist', None)
        if wishlist:
            wishlist_variant_ids = list(wishlist.items.values_list('variant_id', flat=True))

    context = {
        'products': products,
        'wishlist_variant_ids': list(wishlist_variant_ids),
    }
    return render(request, "product_listing.html", context)





def detail_product(request, id):
    """
    return a single product detail page with variants
    """
    try:
        single_product = get_object_or_404(Product, id=id, is_listed=True)

        #get all variants for this product
        # variants = single_product.variants.all()

        variants = single_product.variants.all().order_by('weight')

        #pick one as the dafault
        default_variant = variants.first() if variants.exists() else None
        
        #a dict to hold unique variants and their status
        unique_weights = {}
        unique_flavors = {}

        for variant in variants:
            #for unique weight
            if variant.weight and variant.weight not in unique_weights:
                unique_weights[variant.weight] = {
                    'available' : variant.stock > 0,
                    'variant_id' : variant.id, 
                    'price' : variant.price,
                    # 'weight' : variant.weight,
                    # 'variant.flavor' : variant.flavor,
                }

            #for unique flavor
            if variant.flavor and variant.flavor not in unique_flavors:
                unique_flavors[variant.flavor] = {
                    "variant_id" : variant.id,
                    'variant_id' : variant.id, 
                    'price' : variant.price,
                }

    except Exception as e:
        raise e

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = getattr(request.user, 'wishlist', None)
        if wishlist:
            wishlist_variant_ids = list(wishlist.items.values_list('variant_id', flat=True))
            
    context = {
        "product" : single_product,
        "variants" : variants,
        "default_variant" : default_variant,
        "unique_flavors" : unique_flavors,
        "unique_weights" : unique_weights,
        "current_url" : request.path,
        'wishlist_variant_ids': list(wishlist_variant_ids),
}

    return render(request, "product_detail.html", context)