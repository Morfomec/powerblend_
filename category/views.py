from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control, never_cache
from django.utils import timezone
from utils.pagination import get_pagination
from .models import Category
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.text import slugify

from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

# Create your views here.

# @login_required
@staff_member_required
def admin_category(request):

  """
  Fetch all categories from the db and render them in the the admin category page.
  """

  #to check if clear button is clicekd or not
  if 'clear' in request.GET:
    return redirect('admin_category')

  categories = Category.objects.all().order_by('name')

  #to get query paramters
  search_query = request.GET.get("search", "").strip()
  filter_status = request.GET.get("filter", "")

  #search by name
  if search_query:
    categories = categories.filter(name__icontains=search_query)

  #filter by status
  if filter_status == "listed":
    categories = categories.filter(is_active=True)
  elif filter_status == "unlisted":
    categories = categories.filter(is_active=False)


  #for pagination
  page_obj = get_pagination(request, categories, per_page=5)


  
  context = {
    "active_page": "admin_category",
    # "categories":categories,
    "page_obj":page_obj,
    }       
  return render(request, 'category_management.html', context)


@staff_member_required
def add_category(request):
  """
  TO handle both GET and POST requests for adding a new category
  """

  if request.method == "POST":
    name = request.POST.get('name')
    slug = request.POST.get('slug')
    description = request.POST.get('description')
    parent_id = request.POST.get('parent')
    image = request.FILES.get('image')
    is_active = request.POST.get('is_active') in ["on" , "true", "1", True]


    if not name and not slug:
      slug = slugify(name)
      messages.error(request, "Category name and slug are required fields.")

      #repopulating the form with existing data to avoid losing it

      context = {
        'form':{
          'name':{'value':name},
          'slug':{'value':slug},
          'description':{'value':description},
          'parent':{'value':parent_id},
          'is_active':{'value':is_active},
          'image' : {'value' : image},
        },
        'parent_categories':category.objects.filter(parent__isnull=True),
      }
      return render(request, 'add_category.html', context)

    if image:
      img = Image.open(image)
      img = img.convert('RGB')
      img = img.resize((300, 300), Image.Resampling.LANCZOS)
      img_io =BytesIO()
      img.save(img_io, format='JPEG', quality=90)
      image = ContentFile(img_io.getvalue(), name=image.name)
    
    parent = None
    if parent_id:
      #checking for unique name and slug
      try:
        parent = Category.objects.get(id=parent_id)
      except Category.DoesNotExist:
        messages.error(request, "The selected parent category does not exit.")
        return redirect('add_category')

    try:
      if Category.objects.filter(name__exact=name).exists():
        messages.error(request, f"A category with the name '{name}' already exists.")
        return redirect('add_category')
      if Category.objects.filter(slug__exact=slug).exists():
        messages.error(request, f"A category with the slug '{slug}' already exists.")
        return redirect('add_category')

      

      #creating and saving name and slug
      new_category = Category(
        name=name,
        # slug=slug,
        description=description,
        parent=parent,
        image=image,
        is_active=is_active
      )
      new_category.save()

      messages.success(request, f"Category '{name}' added successfully!")
      return redirect('admin_category')

    except Exception as e:
      messages.error(request, f"An error occured: {e}")
      return redirect('admin_category')

  else:
    parent_categories = Category.objects.filter(parent__isnull=True)
    context = {
      "form":{},
      "parent_categories": parent_categories,
      "mode":"add",
      "active_page": "add_category"
    }
  return render(request, 'add_category.html', context)


@staff_member_required
def edit_category(request, category_id):
  """
  Handle both GET and POST requests for editing an existing category.
  """

  category = get_object_or_404(Category, id=category_id)

  if request.method == 'POST':
    name = request.POST.get('name')
    slug = request.POST.get('slug')
    description = request.POST.get('description')
    parent_id = request.POST.get('parent')
    image = request.FILES.get('image')
    is_active = request.POST.get('is_active') in ["on", "true", "1", True]

    if not name or not slug:
      messages.error(request, "Category name and slug are required fields.")
      return redirect('edit_category', category_id=category.id)

    #to handle parent
    parent = None
    if parent_id:
      try:
        parent = Category.objects.get(id=parent_id)
        if parent.id == category.id:
          messages.error(request, "A category cannot be its own parent.")
          return redirect('edit_category', category_id=category.id)
      except Category.DoesNotExist:
        messages.error(request, "The selected parent category does not exist.")
        return redirect('edit_category', category_id=category.id)

    try:
      #check for unique name and slug but excluding the current category details itself
      if Category.objects.filter(name=name).exclude(id=category.id).exists():
        messages.error(request, f"A category with the name '{name}' already exists.")
        return redirect('edit_category', category_id=category.id)
      
      if Category.objects.filter(slug=slug).exclude(id=category.id).exists():
        messages.error(request, f"A category with the slug '{slug}' aleady exists.")
        return redirect('edit_category', category_id=category.id)

      #updating category fields
      category.name=name
      category.slug=slug
      category.description = description
      category.parent=parent
      category.is_active=is_active

      #replace only if a new images is uploaded

      if image:
        category.image=image
      
      category.save()

      messages.success(request, f"Category '{name}' updated successfully!")
      return redirect('admin_category')

    except Exception as e:
      message.success(request, f"An error occurreed: {e}")
      return redirect('edit_category', category_id=category.id)

  else:
    parent_categories = Category.objects.filter(parent__isnull=True).exclude(id=category.id)

    context = {
      "form":{
        "name":{"value":category.name},
        "slug":{"value":category.slug},
        "description":{"value":category.description},
        "parent":{"value":category.parent.id if category.parent else ''},
        "is_active":{"value":category.is_active},
        "image":{"value":None},
      },
      "category":category, #this is what pre-fills the form fields
      "parent_categories": parent_categories,
      "mode":"edit",
      "active_page": "edit_category"
    }
    return render(request, 'add_category.html', context)

@staff_member_required
def toggle_listing(request, category_id):
  category = get_object_or_404(Category, id=category_id)
  category.is_active =not category.is_active
  category.save()
  # messages.success(request, f"Category {'unlisted' if not category.is_active else 'relisted'} successfully!")
  return redirect('admin_category')