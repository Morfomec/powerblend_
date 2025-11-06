from category.models import Category

def footer_product_links(request):
    """fetching the categories from the db and clickable link is been made for 
    at footer so that it is available everywhere the footer is """

    try:
        links = Category.objects.values_list('name', flat=True)

    except Exception:
        links=[]
    
    return {'product_link': links}