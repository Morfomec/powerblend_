from django.utils import timezone
from decimal import Decimal
from django.db.models import Q
from .models import Offer




def get_best_offer_for_product(product):
    now = timezone.now()

    product_offers = Offer.objects.filter(offer_type='product', products=product, active=True, start_date__lte=now).filter(Q(end_date__gte=now) | Q(end_date__isnull=True))

    category_offers = Offer.objects.filter(offer_type='category',categories=product.category, active=True, start_date__lte=now).filter(Q(end_date__gte=now) | Q(end_date__isnull=True))

    all_offers = list(product_offers) + list(category_offers)

    if not all_offers:
        print(f"No offers found for product {product.name}")
        return None

    # Ensure discount_percent is valid
    valid_offers = [o for o in all_offers if o.discount_percent is not None]

    if not valid_offers:
        print(f"No valid discount_percent for product {product.name}")
        return None

    best_offer = max(valid_offers, key=lambda o: o.discount_percent)
    print(f"Best offer for {product.name}: {best_offer.name} ({best_offer.discount_percent}%)")
    return best_offer

    # product_discount = max([p.discount_percent for p in product_offers], default=Decimal('0'))
    # category_discount = max([c.discount_percent for c in category_offers], default=Decimal('0'))

    # best_discount = max(product_discount, category_discount)
    # return best_discount

def get_discounted_price(product):
    """
    Return the product price after applying the best available offers
    """

    best_offer = get_best_offer_for_product(product)
    if best_offer:
        return product.price * (1 - best_offer.discount_percent / 100)
    return product.price
    # return product.price * (1- (discount / 100))


def get_discount_info_for_variant(variant):
    """
    returns a dict with price info for a varian, including offers
    """
    from products.models import Product, ProductVariant

    best_offer = get_best_offer_for_product(variant.product)
    variant_price = variant.price

    if best_offer and best_offer.active and (best_offer.start_date <= timezone.now() and (best_offer.end_date is None or best_offer.end_date >=  timezone.now())):

        discount_percent = Decimal(best_offer.discount_percent)
        discount_amount = (variant_price * discount_percent) / 100
        discounted_price = variant_price - discount_amount
        
        return {
            'price' : round(discounted_price,2),
            'original_price' : round(variant_price,2),
            'save_price' : round(discount_amount,2),
            'offer_name' : best_offer.name.title(),
            'discount_percent' : discount_percent,
        }

    # if no offer
    return {
        'price' : variant_price,
        'original_price' : getattr(variant, 'original_price', variant_price),
        'save_price' : getattr(variant, 'save_price', 0),
        'offer_name' : None,
        'discount_percent' : 0,
    }