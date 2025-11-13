from category.models import Category
from basket.models import Basket, BasketItem
from wishlist.models import Wishlist, WishlistItem

def footer_product_links(request):
    """fetching the categories from the db and clickable link is been made for 
    at footer so that it is available everywhere the footer is """

    try:
        links = Category.objects.values_list('name', flat=True)

    except Exception:
        links=[]
    
    return {'product_link': links}



def wishlist_basket_item_counts(request):

    """
    to fetch the count of wishlist and basket items and return to show it on the icon
    on header_layout.html
    """
   
    wishlist_count = 0
    basket_count = 0

    if request.user.is_authenticated:
        try:
            wishlist = request.user.wishlist
            wishlist_count = wishlist.items.count()
        except Exception:
            wishlist_count = 0

        try:
            basket = request.user.basket
            basket_count = sum(item.quantity for item in basket.items.all())
        except Exception:
            basket_count = 0

    # MUST return a dict
    return {
        'wishlist_count': wishlist_count,
        'basket_count': basket_count,
    }