from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from products.models import Product, ProductVariant
from category.models import Category
from wishlist.models import Wishlist, WishlistItem
from django.db.models import Q, Sum, Min, Max 
from offers.models import Offer
from offers.utils import get_best_offer_for_product, get_discount_info_for_variant
from collections import OrderedDict
from django.http import JsonResponse

# Create your views here.



# @never_cache
# @login_required(login_url='login')
def home_view(request):
    """
    To view the products in the home page
    """


    products = Product.objects.filter(is_listed=True).prefetch_related("variants")
    # variant = ProductVariant.objects.all()

    category_selected = request.GET.get('category')
    
    if category_selected:
        products = products.filter(category__name__iexact=category_selected)


    for product in products:
        product.best_offer = get_best_offer_for_product(product)
        variants = list(product.variants.all())

        for variant in variants:
            variant.discount_info = get_discount_info_for_variant(variant)

        product.display_variant = variants[0] if variants else None
      

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_variant_ids = wishlist.items.values_list('variant_id', flat=True)

    categories = Category.objects.all()

    category_pills = ['WHEY', 'ISOLATE', 'VITAMINS', 'CREATINE']

    context = {
        'products': products,
        'wishlist_variant_ids': list(wishlist_variant_ids),
        'categories' : categories,
        'category_selected' : category_selected,
        'category_pills' : category_pills,
    }
    return render(request, "home.html", context)



def list_products(request):
    """
    return products list page
    """


    products = Product.objects.filter(is_listed=True).prefetch_related("variants")

    # search
    search_query = request.GET.get("search")
    
    if search_query:
        products = products.filter (
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    # filter by category

    category_id = request.GET.get("category")

    if category_id:
        products=products.filter(category_id=category_id)


    #filter by price

    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price:
        products = products.filter(variants__price__gte=min_price)
    if max_price:
        products = products.filter(variants__price__lte=max_price)

    


    #sorting

    sort_option = request.GET.get("sort")

    products = products.annotate(
    min_price=Min("variants__price"),
    max_price=Max("variants__price")
    )

    if sort_option == "price_low":
        products = products.order_by("min_price")
    elif sort_option == "price_high":
        products = products.order_by("-max_price")
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

    # for product in products:
    #     product.best_offer = get_best_offer_for_product(product)


    for product in products:
        product.best_offer = get_best_offer_for_product(product)

        available_variants = product.variants.filter(stock__gt=0)
        if available_variants.exists():
            cheapest_variant = available_variants.order_by('price').first()
            discount_info = get_discount_info_for_variant(cheapest_variant)
            product.display_variant = discount_info
        
            # get_discount_info_for_variant(cheapest_variant)
            # product.display_variant = cheapest_variant
        else:
            product.display_variant = None
        # for variant in product.variants.all():
        #     variant.discount_info = get_discount_info_for_variant(variant)

    categories = Category.objects.all()



    context = {

        'products': products,
        'wishlist_variant_ids': wishlist_variant_ids,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'min_price': min_price,
        'max_price': max_price,
        'sort_option': sort_option,
    }
    return render(request, "product_listing.html", context)





def detail_product(request, id):
    """
    Return a single product detail page with variants, consistent with home discount logic.
    """
    try:
        single_product = get_object_or_404(
            Product.objects.prefetch_related('variants').annotate(total_stock=Sum('variants__stock')),
            id=id,
            is_listed=True
        )

        variants = single_product.variants.all().order_by('weight')

        if not variants.exists():
            messages.warning(request, "No variants available for this product.")
            return redirect('list_products')

        # Apply discount info just like home view
        for variant in variants:
            variant.discount_info = get_discount_info_for_variant(variant)

        # Apply best product-level offer
        best_offer = get_best_offer_for_product(single_product)

        # Update each variant’s price after considering best offer
        for variant in variants:
            base_price = variant.discount_info['price']
            if best_offer:
                variant.offer_price = variant.discount_info['price']
            else:
                variant.offer_price = base_price


        # Handle unique weights & flavors

        unique_weights = {}
        unique_flavors = {}

        for variant in variants:
            if variant.weight and variant.weight not in unique_weights:
                unique_weights[variant.weight] = {
                    'available': variant.stock > 0,
                    'variant_id': variant.id,
                    'price': variant.offer_price,
                    'original_price': variant.discount_info.get('original_price'),
                    'save_amount': variant.discount_info.get('save_amount'),
                    'stock': variant.stock,
                }

            if variant.flavor and variant.flavor not in unique_flavors:
                unique_flavors[variant.flavor] = {
                    'available': variant.stock > 0,
                    'variant_id': variant.id,
                    'price': variant.offer_price,
                    'original_price': variant.discount_info.get('original_price'),
                    'save_amount': variant.discount_info.get('save_amount'),
                    'stock': variant.stock,
                }

        selected_weight = request.GET.get('weight')
        selected_flavor = request.GET.get('flavor')
        selected_variant = None

        for variant in variants:
            # Get the text value whether it’s a related object or a direct string
            flavor_name = getattr(variant.flavor, "flavor", None)
            weight_name = getattr(variant.weight, "weight", None)

            # Case-insensitive comparison for safety
            if (not selected_flavor or (flavor_name and flavor_name.lower() == selected_flavor.lower())) and \
            (not selected_weight or (weight_name and weight_name.lower() == selected_weight.lower())):
                selected_variant = variant
                break

        # Fallback to first variant if no match found
        if not selected_variant:
            selected_variant = variants.first()
        
        print("Selected flavor:", selected_flavor)
        print("Selected weight:", selected_weight)
        print("Final variant:", selected_variant.flavor, selected_variant.weight)

        # ✅ Corrected typo and logic
        for variant in variants:
            weight_match = (not selected_weight or variant.weight == selected_weight)
            flavor_match = (not selected_flavor or variant.flavor == selected_flavor)
            if weight_match and flavor_match:
                selected_variant = variant
                break

        if not selected_variant:
            selected_variant = variants.first()

        selected_variant_info = {
            'id': selected_variant.id,
            'price': selected_variant.offer_price,
            'original_price': selected_variant.discount_info.get('original_price'),
            'save_amount': selected_variant.discount_info.get('save_amount'),
            'weight': selected_variant.weight,
            'flavor': selected_variant.flavor,
            'stock': selected_variant.stock,
            'has_discount': bool(selected_variant.discount_info.get('save_amount', 0) > 0),
        }

        # Related variant groupings
        variants_by_weight = [v for v in variants if v.weight == selected_variant.weight]
        variants_by_flavor = [v for v in variants if v.flavor == selected_variant.flavor]

        available_flavors = OrderedDict()
        for variant in variants:
            if variant.flavor and variant.flavor.flavor not in available_flavors:
                available_flavors[variant.flavor.flavor] = {
                    'variant_id': variant.id,
                    'available': variant.stock > 0,
                    'weight': variant.weight,
                    'flavor_obj': variant.flavor,  # keep object if needed
                }

        available_weights = OrderedDict()
        for variant in variants:
            if variant.weight and variant.weight not in available_weights:
                available_weights[variant.weight] = {
                    'variant_id': variant.id,
                    'available': variant.stock > 0,
                    'weight_obj': variant.weight,  # keep object if needed
                    'flavor': variant.flavor,
                }

    except Exception as e:
        raise e

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = getattr(request.user, 'wishlist', None)
        if wishlist:
            wishlist_variant_ids = list(wishlist.items.values_list('variant_id', flat=True))

    context = {
        "product": single_product,
        "variants": variants,
        "selected_variant": selected_variant,
        "selected_variant_info": selected_variant_info,
        "unique_flavors": unique_flavors,
        "unique_weights": unique_weights,
        "available_flavors": available_flavors if available_flavors else unique_flavors,
        "available_weights": available_weights if available_weights else unique_weights,
        "best_offer": best_offer,
        "wishlist_variant_ids": wishlist_variant_ids,
        # 'weight': selected_variant.weight,
        # 'flavor': selected_variant.flavor,
    }
    print("Selected variant info:", selected_variant_info)
    return render(request, "product_detail.html", context)



def search_suggestions(request):
    """
    Handle AJAX live seacrh requests and return product name sugesstions.
    """

    query = request.GET.get('q', '')
    suggestions = []

    if query:
        products = Product.objects.filter(name__icontains=query)[:5]
        suggestions = [{'id': p.id, 'name': p.name, 'url': p.get_absolute_url()} for p in products]

    return JsonResponse({'suggestions' : suggestions})