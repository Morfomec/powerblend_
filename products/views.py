from django.shortcuts import render, redirect,get_object_or_404
from .models import Product, ProductImage
from category.models import Category
from utils.pagination import get_pagination
from django.contrib import messages
from .forms import ProductForm, ProductImageForm
from django.urls import reverse

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
        products = products.filter(name__icontains=search_query)
    
    #filter by status
    filter_status = request.GET.get("filter", "")
    if filter_status == 'listed':
        products = products.filter(is_listed=True)
    elif filter_status == 'unlisted':
        products = products.filter(is_listed=False)
    elif filter_status == 'out-of-stock':
        products = products.filter(stock=0)
    elif filter_status == 'low-stock':
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
    
    current_page = request.GET.get('page', '1')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        is_listed = request.POST.get('is_listed') in ["on" , "true", "1", True]

        uploaded_images = request.FILES.getlist('images')
        
        if not name or not description or not category or not price:
            messages.error(request, "Field inputs are missing!!")

            categories = Category.objects.all()

            #repopulate the form with existing data to avoid losing it

            context = {
                'form':{
                    'name':{'value':name},
                    'description':{'value':description},
                    'category':{'value':category},
                    'price':{'value':price},
                    'stock':{'value':stock},
                    'is_listed':{'value':is_listed},
                },
                'categories': categories,
                "mode":"add",
                "active_page":"add_product",
            }
            return render(request, 'add_product.html', context)

        #have check for minimum number of images
        if not uploaded_images or len(uploaded_images) < 3:
            messages.error(request, "Please upload at least 3 product images.")

            #repopulate the form again

            categories = Category.objects.all()
            context = {
                'form':{
                    'name':{'value':name},
                    'description':{'value':description},
                    'category':{'value':category},
                    'price':{'value':price},
                    'stock':{'value':stock},
                    'is_listed':{'value':is_listed},
                },
                'categories': categories,
                "mode":"add",
                "active_page":"add_product",
            }
            return render(request, 'add_product.html', context)


        try:
            #save products now
            category = get_object_or_404(Category, id=category)
            product = Product.objects.create(
                name = name,
                description=description,
                category=category,
                price=price,
                stock=stock if stock else 0,
                is_listed=is_listed,
            )
            # return render(request, 'add_product.html', context)


            #to handle multiple images
            # if request.FILES.getlist('images'):
            for img in request.FILES.getlist('images'):
                ProductImage.objects.create(product=product, image=img)

            messages.success(request, f"Product '{name}' added successfully!")
            return redirect(f"{reverse('admin_products')}?page={current_page}")
        
        except Exception as e:
            messages.error(request, f"An error occurred:{e}")
            return redirect('add_product')

    else:
        categories = Category.objects.all()
        context = {
            "form" : {},
            "categories":categories,
            "mode":"add",
            "active_page":"add_product"
        }

        
        return render(request, 'add_product.html', context)


def add_variants(request):
    l
    return render(request, 'add_variants.html')

# def edit_product(request, product_id):
#     """
#     Handle both GET and POST requests for editing an existing products.
#     """
#     product = get_object_or_404(Product,id=product_id)

#     if request.method == 'POST':
#         name = request.POST.get('name')
#         description = request.POST.get('description')
#         category = request.POST.get('category')
#         price = request.POST.get('price')
#         stock = request.POST.get('stock')
#         is_listed = request.POST.get('is_listed') in ["on", "true", "1", True]

        
#         #validation 
        
#         if not name or not description or not category or not price:
#             messages.error(request, " Please fill in all required fields.")
#             categories = Category.objects.all()
#             context = {
#                 'product':product,
#                 'categories':categories,
#                 'mode':"edit",
#                 "active_page":"edit_product",
#             }
#             return render(request, 'add_product.html', context)

#         # handle uploaded images

#         uploaded_images = request.FILES.getlist('images')

#         try:

#             #to get the selected category
#             category_id = request.POST.get('category')
#             category_obj = get_object_or_404(Category, id=category_id)

#             #update the product fields
#             product.name = name
#             product.description = description
#             product.category = category_obj
#             product.price = price
#             product.stock = stock
#             product.is_listed = is_listed
            
#             product.save()

#             # to save uploaded images without removing exisiting oen

#             if uploaded_images:
#                 for img in uploaded_images:
#                     ProductImage.objects.create(product=product, image=img)

#             messages.success(request, f"Product '{name}' updated successfully!")
#             return redirect('admin_products')

#         except Exception as e:
#             messages.error(request, f"An error occured:{e}")
#             return redirect('edit_product', product_id=product.id)

#     else: 
#         #opening page first time

#         categories = Category.objects.all()
#         context = {
#             "form":{
#                 "name":{"value":product.name},
#                 "description":{"value":product.description},
#                 "category":{"value":product.category.id if product.category else None},
#                 "price":{"value":product.price},
#                 "stock":{"value":product.stock},
#                 "is_listed":{"value":product.is_listed},
                
#             },
#             "product":product,
#             "categories":categories,
#             "mode":"edit",
#             "active_page":"edit_product",
#         }
#         return render(request, 'add_product.html', context)



def edit_product(request, product_id):
    """
    Handle both GET and POST requests for editing an existing products.
    """

    product = get_object_or_404(Product, id=product_id)

    #capture the page number
    current_page = request.GET.get('page', '1')

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        uploaded_images = request.FILES.getlist('images')

        if form.is_valid():
            product = form.save() #it updates the products

            # to handle image uploads (keeps old one and add new)
            if uploaded_images:
                for img in uploaded_images:
                    ProductImage.objects.create(product=product, image=img)

            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect(f"{reverse('admin_products')}?page={current_page}")
        else:
            message.error(request, "Please fix the error.")

    else:
        form = ProductForm(instance=product)
    
    categories = Category.objects.all()

    context = {
        "form": form,
        "product": product,
        "categories": categories,
        "mode": "edit",
        "active_page": "edit_product",
    }
    return render(request, 'add_product.html', context)

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    current_page = request.GET.get('page', '1')

    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' was deleted successfully.")
        return redirect(f"{reverse('admin_products')}?page={current_page}")

    messages.error(request, "Invalid request for product deletion.")
    return redirect('edit_product', product_id=product_id)

# def add_product(request):
#     if request.method == "POST":
#         form = ProductForm(request.POST)
#         formset = ProductImageFormSet(request.POST, request.FILES)

#         if form.is_valid() and formset.is_valid():
#             product = form.save()
#             images = formset.save(commit=False)

#             if len(images) < 3:  # enforce min 3 images
#                 messages.error(request, "Please upload at least 3 images")
#             else:
#                 for i, img in enumerate(images):
#                     img.product = product
#                     if i == 0:
#                         img.is_primary = True
#                     img.save()
#                 messages.success(request, "Product added successfully")
#                 return redirect("admin_products")
#         else:
#             messages.error(request, "Please fix the errors below")
#     else:
#         form = ProductForm()
#         formset = ProductImageForm()

#     return render(request, "add_product.html", {
#         "form": form,
#         "formset": formset,
#         "mode": "add"
#     })

def toggle_product_listing(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_listed = not product.is_listed
    product.save()

    status = "listed" if product.is_listed else "unlisted"
    messages.success(request, f"Product '{product.name}' is now {status}.")

    return redirect('admin_products')