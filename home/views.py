from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from products.models import Product, ProductVariant
from category.models import Category
from wishlist.models import Wishlist, WishlistItem
from django.db.models import Q, Sum, Min, Max, Value, F, Case, When, DecimalField, OuterRef, Subquery
from offers.models import Offer
from offers.utils import get_best_offer_for_product, get_discount_info_for_variant
from collections import OrderedDict
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from django.db.models.functions import Coalesce
from django.templatetags.static import static
from django.utils import timezone
from admin_app.models import Banner, Coupon
from reviews.models import Review
from reviews.forms import ReviewForm
from orders.models import OrderItem
from django.db.models import Avg

# from django.utils import timezone
# Create your views here.



def home_view(request):
    """
    To view the products in the home page
    """

    category_selected = request.GET.get('category')

    # If category is selected, show filtered products (not random)
    if category_selected:
        products = Product.objects.filter(
            is_listed=True,
            category__name__iexact=category_selected
        ).prefetch_related("variants")
    else:
        # Only show 4 random products when no category is selected
        products = Product.objects.filter(
            is_listed=True
        ).prefetch_related("variants").order_by('?')[:4]

    best_selling_products = (
        Product.objects.filter(
            is_listed=True,
            variants__stock__gt=0) .annotate(
            total_sold=Coalesce(
                Sum("variants__orderitems__quantity"),
                Value(0))) .filter(
                    total_sold__gt=0) .order_by('-total_sold') .prefetch_related(
                        'images',
                        'variants')[
                            :4])

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
            wishlist_variant_ids = wishlist.items.values_list(
                'variant_id', flat=True)

    categories = Category.objects.all()

    category_pills = ['WHEY PROTEIN', 'ISOLATE', 'VITAMINS', 'CREATINE']

    promo_images = {
        "WHEY": "images/promo/whey-promo.avif",
        "ISOLATE": "images/promo/isolate-promo.avif",
        "VITAMINS": "images/promo/vitamins-promo.avif",
        "CREATINE": "images/promo/creatine-promo.avif",
        
    }


    

    for product in best_selling_products:
        cat_name = product.category.name.upper()
        relative_path = promo_images.get(
            cat_name, "images/default-category.jpg")
        product.category_image = static(relative_path)

    active_banners = Banner.objects.filter(
        is_active=True).order_by('-created_at')

    context = {
        'products': products,
        'wishlist_variant_ids': list(wishlist_variant_ids),
        'categories': categories,
        'category_selected': category_selected,
        'category_pills': category_pills,
        'best_selling_products': best_selling_products,
        'promo_images': promo_images,
        'active_banners': active_banners,
        # 'coupon_data': coupon_data,
    }
    return render(request, "home.html", context)


def list_products(request):
    """
    return products list page
    """

    products = Product.objects.filter(
        is_listed=True).prefetch_related("variants")

    # search
    search_query = request.GET.get("search")

    if search_query:
        products = products.filter(Q(name__icontains=search_query) | Q(
            description__icontains=search_query))

    # filter by category
    category_id = request.GET.get("category")

    if category_id:
        products = products.filter(category_id=category_id)

    # Get current time for checking active offers
    now = timezone.now()

    # Subquery to get the best product offer discount
    product_offer_discount = Offer.objects.filter(
        products=OuterRef('pk'),
        offer_type='product',
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-discount_percent').values('discount_percent')[:1]

    # Subquery to get the best category offer discount
    category_offer_discount = Offer.objects.filter(
        categories=OuterRef('category'),
        offer_type='category',
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-discount_percent').values('discount_percent')[:1]

    # Annotate products with min/max prices and discounted prices
    products = products.annotate(
        min_variant_price=Min("variants__price"),
        max_variant_price=Max("variants__price"),
        product_discount=Subquery(product_offer_discount),
        category_discount=Subquery(category_offer_discount),
        # Calculate the best discount (product offer takes priority over
        # category offer)
        best_discount=Case(
            When(product_discount__isnull=False, then=F('product_discount')),
            When(category_discount__isnull=False, then=F('category_discount')),
            default=Value(0),
            output_field=DecimalField()
        ),
        # Calculate minimum price after discount
        min_discounted_price=F('min_variant_price') *
        (100 - F('best_discount')) / 100
    )

    # filter by price (using discounted price)
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    try:
        if min_price:
            min_price_decimal = Decimal(min_price)
            if min_price_decimal < 0:
                messages.warning(request,
                                 "Minimum price cannot be negative.",
                                 extra_tags='mini_price_not_negative')
            else:
                products = products.filter(
                    min_discounted_price__gte=min_price_decimal)

        if max_price:
            max_price_decimal = Decimal(max_price)
            if max_price_decimal < 0:
                messages.warning(request,
                                 "Maximum price cannot be negative.",
                                 extra_tags='maxi_price_not_negative')
            else:
                products = products.filter(
                    min_discounted_price__lte=max_price_decimal)

    except (InvalidOperation, ValueError):
        messages.warning(
            request,
            "Price filter must contain valid positive numbers only.",
            extra_tags='positive_numbers_only')

    # sorting
    sort_option = request.GET.get("sort")

    if sort_option == "price_low":
        products = products.order_by("min_discounted_price")
    elif sort_option == "price_high":
        products = products.order_by("-min_discounted_price")
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
            wishlist_variant_ids = list(
                wishlist.items.values_list(
                    'variant_id', flat=True))

    for product in products:
        product.best_offer = get_best_offer_for_product(product)

        available_variants = product.variants.filter(stock__gt=0)
        if available_variants.exists():
            cheapest_variant = available_variants.order_by('price').first()
            discount_info = get_discount_info_for_variant(cheapest_variant)
            product.display_variant = discount_info
        else:
            product.display_variant = None

    today = timezone.now().date() 
    active_coupon = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=today,
        valid_to__gte=today,
    ).order_by('-discount_amount').first()

    coupon_data=None

    if active_coupon:
        coupon_data = {
            'code' : active_coupon.code,
            'minimum_amount' : active_coupon.minimum_amount,
            'discount_amount' : active_coupon.discount_amount,

        }

    new_variant = ProductVariant.objects.filter(
        product__name__icontains='whey protein',
        flavor__flavor__icontains="cookies & cream",
        is_listed = True,
        product__is_listed = True,
        stock__gt=0,
    ).select_related('product').first()
    
    new_product_id = new_variant.product.id if new_variant else None

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
        'coupon_data': coupon_data,
        'new_product_id': new_product_id,
    }
    return render(request, "product_listing.html", context)


def detail_product(request, id):
    """
    Return a single product detail page with variants, consistent with home discount logic.
    """
    try:
        single_product = get_object_or_404(
            Product.objects.prefetch_related('variants').annotate(
                total_stock=Sum('variants__stock')), id=id, is_listed=True)

        variants = single_product.variants.all().order_by('weight')

        if not variants.exists():
            messages.warning(
                request, "No variants available for this product.")
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

        today = timezone.now().date() 
        active_coupon = Coupon.objects.filter(
            is_active=True,
            valid_from__lte=today,
            valid_to__gte=today,
        ).order_by('-discount_amount').first()

        coupon_data=None

        if active_coupon:
            coupon_data = {
                'code' : active_coupon.code,
                'minimum_amount' : active_coupon.minimum_amount,
                'discount_amount' : active_coupon.discount_amount,

            }

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

            flavor_name = getattr(variant.flavor, "flavor", None)
            weight_name = getattr(variant.weight, "weight", None)

            if (not selected_flavor or (flavor_name and flavor_name.lower() == selected_flavor.lower())) and (
                    not selected_weight or (weight_name and weight_name.lower() == selected_weight.lower())):
                selected_variant = variant
                break

        if not selected_variant:
            selected_variant = variants.first()

        for variant in variants:
            weight_match = (
                not selected_weight or variant.weight == selected_weight)
            flavor_match = (
                not selected_flavor or variant.flavor == selected_flavor)
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
            'has_discount': bool(
                selected_variant.discount_info.get(
                    'save_amount',
                    0) > 0),
        }

        variants_by_weight = [
            v for v in variants if v.weight == selected_variant.weight]
        variants_by_flavor = [
            v for v in variants if v.flavor == selected_variant.flavor]

        available_flavors = OrderedDict()
        for variant in variants:
            if variant.flavor and variant.flavor.flavor not in available_flavors:
                available_flavors[variant.flavor.flavor] = {
                    'variant_id': variant.id,
                    'available': any(v.stock > 0 for v in variants if v.flavor == variant.flavor),
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
            wishlist_variant_ids = list(
                wishlist.items.values_list(
                    'variant_id', flat=True))

    best_selling_products = (
        Product.objects.filter(
            is_listed=True,
            variants__stock__gt=0) .annotate(
            total_sold=Coalesce(
                Sum("variants__orderitems__quantity"),
                Value(0))) .filter(
                    total_sold__gt=0) .order_by('-total_sold') .prefetch_related(
                        'images',
                        'variants')[
                            :4])

    # review logic

    selected_variant_reviews = Review.objects.filter(
        product=single_product
    ).select_related('user').order_by('-created_at')

    avg_rating = selected_variant_reviews.aggregate(
        Avg('rating')
    )['rating__avg'] or 0

    total_reviews = selected_variant_reviews.count()


    purchased = False
    if request.user.is_authenticated:
        purchased = OrderItem.objects.filter(
            order__user = request.user,
            variant = selected_variant,
            status = 'delivered',
            is_cancelled = False,
            is_returned = False,
        ).exists()

    context = {
        "product": single_product,
        "variants": variants,
        "selected_variant": selected_variant,
        "selected_variant_info": selected_variant_info,
        'best_selling_products': best_selling_products,
        "unique_flavors": unique_flavors,
        "unique_weights": unique_weights,
        "available_flavors": available_flavors if available_flavors else unique_flavors,
        "available_weights": available_weights if available_weights else unique_weights,
        "best_offer": best_offer,
        "wishlist_variant_ids": wishlist_variant_ids,
        'coupon_data': coupon_data,
        'reviews': selected_variant_reviews,
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'purchased': purchased,
        'review_form': ReviewForm()
        # 'weight': selected_variant.weight,
        # 'flavor': selected_variant.flavor,
    }

    return render(request, "product_detail.html", context)


def search_suggestions(request):
    """
    Handle AJAX live seacrh requests and return product name sugesstions.
    """

    query = request.GET.get('q', '')
    suggestions = []

    if query:
        products = Product.objects.filter(name__icontains=query)[:5]
        suggestions = [{'id': p.id, 'name': p.name,
                        'url': p.get_absolute_url()} for p in products]

    return JsonResponse({'suggestions': suggestions})


def about_us(request):

    return render(request, 'about_us.html')


def contact_us(request):
    # product_link = ['Whey', 'Isolate', 'Vitamins', 'Creatine']
    # context = {
    #     'product_link' : product_link,
    # }
    return render(request, 'contact_us.html')


def footer(request):
    product_link = ['Whey', 'Isolate', 'Vitamins', 'Creatine']
    context = {
        'product_link': product_link,
    }
    return render(request, 'includes/footer_layout.html', context)
