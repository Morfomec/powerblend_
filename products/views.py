from django.shortcuts import render, redirect,get_object_or_404, HttpResponse
from .models import Product, ProductImage, Flavor, Weight, ProductVariant
from category.models import Category
from utils.pagination import get_pagination
from django.contrib import messages
from .forms import ProductForm,  ProductVariantForm, FlavorForm, WeightForm
from django.urls import reverse
from django.db.models import Sum
from django.views.decorators.http import require_POST
from offers.utils import get_best_offer_for_product,get_discount_info_for_variant



# Create your views here.

def admin_products(request):
    """       
    Fetch all products from the db and rendder them in the product management page.
    """


    #to check if clear button is clicked or not
    if 'clear' in request.GET:
        return redirect('admin_products')
            
    # products = Product.objects.filter(is_listed=True, category__is_active=True).order_by('name')
    products = Product.objects.all().order_by('name')

    products = products.annotate(total_stock=Sum('variants__stock'))

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
        products = products.filter(total_stock=0)
    elif filter_status == 'low-stock':
        products = products.filter(total_stock__lte=5)

    
    #for pagination 
    page_obj= get_pagination(request, products, per_page=5)
    products = Product.objects.all().order_by('name')
    
    context = {
        "product" : products,
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
        
        if not name or not description or not category:
            messages.error(request, "Field inputs are missing!!")

            categories = Category.objects.all()

            #repopulate the form with existing data to avoid losing it

            context = {
                'form':{
                    'name':{'value':name},
                    'description':{'value':description},
                    'category':{'value':category},
                    # 'price':{'value':price},
                    # 'stock':{'value':stock},
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
                    # 'price':{'value':price},
                    # 'stock':{'value':stock},
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
                # price=price,
                # stock=stock if stock else 0,
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
            messages.error(request, f"An error occurred: {e}")
            categories = Category.objects.all()
            context = {
                'form': {
                    'name': {'value': name},
                    'description': {'value': description},
                    'category': {'value': category},
                    'is_listed': {'value': is_listed},
                },
                'categories': categories,
                "mode": "add",
                "active_page": "add_product",
            }
            
            return render(request, 'add_product.html', context)

    else:
        categories = Category.objects.all()
        context = {
            "form" : {},
            "categories":categories,
            "mode":"add",
            "active_page":"add_product",
        }

        
        return render(request, 'add_product.html', context)




def add_variants(request, product_id):
    """
    Add and list variants of a given product.
    Variants are combinations of existing flavors and weights.
    """

    product = get_object_or_404(Product, id=product_id)
    #fetching product variant
    variants_queryset = product.variants.all().order_by("-id") 

    
    #pagination applied 
    page_obj =get_pagination(request, variants_queryset, per_page=5)


    if request.method == 'POST':
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            flavor = form.cleaned_data.get("flavor")
            weight = form.cleaned_data.get("weight")
            price = form.cleaned_data.get("price")
            stock = form.cleaned_data.get("stock")


            variant, created = ProductVariant.objects.get_or_create(
                product = product,
                flavor = flavor,
                weight = weight,
                defaults = {'price':price, 'stock':stock},
            )

            if created:
                messages.success(request, f"New variant added for  {product.name}.")
            else:
                variant.price = price
                variant.stock = stock
                variant.save(update_fields=["price", "stock"])
                messages.success(request, f"Updated existing variant for {product.name}.")
            return redirect("add_variants", product_id=product_id)
        else: 
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductVariantForm()

    context = {
        "product" : product,
        "form" : form,
        "page_obj" : page_obj,
        "variants" : page_obj,
        "product_id" : product.id, 
    }

    return render(request, "add_variants.html", context)



from django.db import IntegrityError

def edit_variant(request, variant_id):
    """
    Handle GET and POST requests for editing an existing product variant.

    Allows updates to price, stock, and other fields.
    Prevents saving duplicate (product, flavor, weight) combinations.
    """

    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product
    current_page = request.GET.get('page', '1')

    # Store original combo before the form modifies it
    original_flavor = variant.flavor
    original_weight = variant.weight

    if request.method == 'POST':
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            new_flavor = form.cleaned_data.get("flavor")
            new_weight = form.cleaned_data.get("weight")

            # Check only if flavor or weight changed
            if (new_flavor != original_flavor) or (new_weight != original_weight):
                duplicate = ProductVariant.objects.filter(
                    product=product,
                    flavor=new_flavor,
                    weight=new_weight
                ).exclude(id=variant.id)
                if duplicate.exists():
                    messages.error(request, "This variant already exists!")
                    return render(request, 'add_variants.html', {
                        'product': product,
                        'variant': variant,
                        'form': form,
                        'mode': "edit",
                    })

            try:
                form.save()
                messages.success(request, f"Variant updated successfully for {product.name}")
                return redirect(f"{reverse('add_variants', args=[product.id])}?page={current_page}")

            except IntegrityError:
                # Database-level safeguard
                messages.error(request, "This flavor-weight combination already exists!")
                return render(request, 'add_variants.html', {
                    'product': product,
                    'variant': variant,
                    'form': form,
                    'mode': "edit",
                })

    else:
        form = ProductVariantForm(instance=variant)

    context = {
        'product': product,
        'variant': variant,
        'form': form,
        'mode': "edit",
        'active_page': 'edit_variant',
    }
    return render(request, 'add_variants.html', context)





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
            product = form.save()

            # to handle image uploads (keeps old one and add new)
            if uploaded_images:
                for img in uploaded_images:
                    exisiting_image = product.images.filter(image__icontains=img.name).exists()
                    if not exisiting_image:
                        ProductImage.objects.create(product=product, image=img)

            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect(f"{reverse('admin_products')}?page={current_page}")
        else:
            messages.error(request, "Please fix the error.")

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



def manage_attributes(request, product_id):
    """
    Manage variant attributes flavors and weights with forms and pagination.
    """
    product = get_object_or_404(Product, id=product_id)

    flavor_form = FlavorForm()
    weight_form = WeightForm()

    #handling flavor form

    if request.method == 'POST' and "flavor_submit" in request.POST:
        flavor_form = FlavorForm(request.POST)
        if flavor_form.is_valid():
            flavor_form.save()
            messages.success(request, "Flavor added successfully!")
            return redirect('manage_attributes', product_id)
        else:
            messages.error(request, "Please fix the error in the flavor form.")
        

    
    #handling weight form

    elif request.method == 'POST' and "weight_submit" in request.POST:
        weight_form = WeightForm(request.POST)
        if weight_form.is_valid():
            weight_form.save()
            messages.success(request, "Weight added successfully!")
            return redirect('manage_attributes',product_id)
        else:
            messages.error(request, "Please fix the errors in the weight form.")
        
    
    # fetching existing datas of flavor and weight

    flavors = Flavor.objects.all().order_by("-created_at")
    weights = Weight.objects.all().order_by("-created_at")


    #pagination
    flavor_page_obj= get_pagination(request, flavors, per_page=5)
    weight_page_obj= get_pagination(request, weights, per_page=5)

    context = {
        "flavor_form" : flavor_form,
        "weight_form" : weight_form,
        "flavors" : flavors,
        "weights" : weights,
        "flavor_page_obj" : flavor_page_obj,
        "weight_page_obj" : weight_page_obj,
        "flavor_count": flavors.count(),
        "weight_count" : weights.count(),
        "product_id" : product.id,
    }

    return render (request, "manage_variant_attributes.html", context)


def toggle_product_listing(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_listed = not product.is_listed
    product.save()

    status = "listed" if product.is_listed else "unlisted"
    messages.success(request, f"Product '{product.name}' is now {status}.")

    return redirect('admin_products')

@require_POST
def toggle_variant_listing(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    variant.is_listed = not variant.is_listed
    variant.save()

    status = "listed" if variant.is_listed else "unlisted"
    messages.success(request, f"Variant '{variant.flavor}'-'{variant.weight}' is now {status}.")
    return redirect('add_variants', product_id=variant.product.id)




def upload_product_images(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        product = get_object_or_404(Product, id=product_id)
        images = request.FILES.getlist('images')

        for img in images:
            ProductImages.objects.create(product=product, image=img)
        
        messages.success(request, 'Images uploaded successfully.')
        return redirect('admin_products')


def delete_product_image(request, image_id):
    """
    Delete a specific image from a product 
    """

    image = get_object_or_404(ProductImage, id=image_id)
    product = image.product
    remaining_images = product.images.count()

    if request.method == 'POST':
        if remaining_images <= 3:
            messages.error(request, "You must have at least 3 product images.")
        else:    
            image.delete()
            messages.success(request,"Image deleted successfully.")
        return redirect(reverse('edit_product', kwargs={'product_id': product.id}))
    return redirect(reverse('edit_product', kwargs={'product_id': product.id}))


def delete_product(request, product_id):
    return confirm_delete(
        request,
        model=Product,
        object_id=product_id,
        object_name="product",
        redirect_url_name="admin_products",
    )

def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    return confirm_delete(request, model=ProductVariant, object_id=variant_id, object_name="variants", redirect_url_name="add_variants", redirect_kwargs={'product_id' : product_id})



def confirm_delete(request, model, object_id, object_name, redirect_url_name, redirect_kwargs=None):
    
    obj = get_object_or_404(model, id=object_id)

    if request.method == 'POST':

        obj.delete()
        messages.success(request, f"{object_name.capitalize()} deleted successfully.")
        return redirect(reverse(redirect_url_name, kwargs=redirect_kwargs or {}))

    
    context = {
        'object_name' : object_name,
        'object_display' : str(obj),
        'confirm_url' : request.path,
        'cancel_url' : reverse(redirect_url_name, kwargs=redirect_kwargs or {}),

    }

    return render(request, 'confirm_delete.html', context)



