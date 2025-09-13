from django.shortcuts import render, redirect
from .models import Product
from utils.pagination import get_pagination

# Create your views here.

def admin_products(request):
    """
    Fetch all products from the db and rendder them in the product management page.
    """

    #to check if clear button is clicked or not
    if 'clear' in request.GET:
        return redirect('admin_products')
            
    products = Product.objects.all().order_by('name')

    #to get query parameters
    search_query = request.GET.get("search", "").strip()
    #to get by searching name
    if search_query:
        products = products.filter(name__iscontain==search_query)
    
    #filter by status
    filter_status = request.GET.get("filter", "")
    if filter_status == 'listed':
        products = products.filter(is_listed=True)
    elif filter_status == 'unlisted':
        products = products.filter(is_listed=False)
    elif filter_status == 'out of stock':
        products = products.filter(stock=0)
    elif filter_status == 'low stock':
        products = products.filter(stock__lte=5)
    
    #for pagination 
    page_obj= get_pagination(request, products, per_page=5)
    
    context = {
        "active_page": "admin_products",
        "page_obj":page_obj,
    }

    return render(request, 'product_management.html', context)


def add_product(request):
    """
    To handle both GET and POST requests for adding a new product
    """
   
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        is_listed = request.POST.get('is_listed') in ["on" , "true", "1", True]

        
        if not name or not description or not category or not price:
            messages.error(request, "Field inputs are missing!!")

            #repopulation the form with existing data to avoid losing it

            context = {
                'form':{
                    'name':{'value':name},
                    'description':{'value':description},
                    'category':{'value':description},
                    'price':{'value':price},
                    'stock':{'value':stock},
                    'is_listed':{'value':stock},
                },

            }
            return render(request, 'add_product.html', context)
        #save products now
        category = Category.objects.get(id=category)
        product = Product.objects.create(
            name = name,
            description=description,
            category=category,
            price=price,
            stock=stock if stock else 0,
            is_listed=is_listed,
        )

        #to handle multiple images
        if request.FIELS.getlist('images'):
            for img in request.FILES.getlist('images'):
                ProductImage.objects.create(product=product, image=img)

        messages.success(request, f"Product '{name}' added successfully!")
        return redirect('')

    
    return render(request, 'add_product.html')