from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Offer
from .forms import OfferForm
from django.utils import timezone
from products.models import Product
from category.models import Category
from django.db.models import Q

# Create your views here.


@staff_member_required
def admin_offer_list(request):
    """
    to show all offers in admin dashboard
    """

    today = timezone.now()
    offers = Offer.objects.all().order_by('-created_at')

    q = request.GET.get('q', '').strip()
    offer_type = request.GET.get('offer_type', '').strip()
    status = request.GET.get('status', '').strip()

    # to search by offer name
    if q:
        offers = offers.filter(name__icontains=q)

    # filter by offer type
    if offer_type:
        offers = offers.filter(offer_type=offer_type)

    # filter by status
    if status == 'active':
        offers = offers.filter(active=True, end_date__gte=today)
    elif status == 'expired':
        offers = offers.filter(Q(active=False) | Q(end_date__lt=today))

    context = {
        'q': q,
        'status': status,
        'offer_type': offer_type,
        'offers': offers,
        'today': today,
    }
    return render(request, 'offer_list.html', context)


@staff_member_required
def admin_add_offer(request):
    """
    to add new offers
    """

    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_listed=True)

    if request.method == 'POST':
        form = OfferForm(request.POST)

        if form.is_valid():
            offer = form.save(commit=False)
            offer.name = offer.name.strip().lower()
            offer.save()


            # name = form.cleaned_data['name'].strip().lower()
            # offer_type = form.cleaned_data['offer_type']

            # if Offer.objects.filter(
            #         name__iexact=name,
            #         offer_type=offer_type).exists():
            #     messages.error(
            #         request, f"An offer name {name} already exists for this offer type.")
            #     return redirect('admin_add_offer')
            # else:
            #     offer = form.save(commit=False)
            #     offer.name = name
            #     offer.save()

            if offer.offer_type == 'product':
                offer.products.set(request.POST.getlist('products'))
            elif offer.offer_type == 'category':
                offer.categories.set(request.POST.getlist('categories'))

            messages.success(request, 'Offer added successfully.')
            return redirect('admin_offer_list')
    else:
        form = OfferForm()

    context = {
        'form': form,
        'categories': categories,
        'products': products,
    }
    return render(request, 'add_edit_offer.html', context)


@staff_member_required
def admin_edit_offer(request, offer_id):
    """
    to Edit an existing offer
    """

    offer = get_object_or_404(Offer, id=offer_id)
    products = Product.objects.filter(is_listed=True)
    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)

        if form.is_valid():
            offer = form.save(commit=False)
            offer.name = offer.name.strip().lower()
            offer.save()

            # if Offer.objects.filter(
            #         name__iexact=name,
            #         offer_type=offer_type).exclude(
            #         id=offer_id).exists():
            #     messages.error(
            #         request, f"An offer name {name} already exists for this offer type.")

            # else:
            #     offer = form.save(commit=False)
            #     offer.name = name
            #     offer.save()

            if offer.offer_type == 'product':
                offer.products.set(request.POST.getlist('products'))
                offer.categories.clear()
            elif offer.offer_type == 'category':
                offer.categories.set(request.POST.getlist('categories'))
                offer.products.clear()

                # if offer_type == 'product':
                #     selected_products = request.POST.getlist('products')
                #     offer.products.set(selected_products)
                #     offer.categories.clear()
                # elif offer_type == 'category':
                #     selected_categories = request.POST.getlist('categories')
                #     offer.categories.set(selected_categories)
                #     offer.products.clear()

            messages.success(request, 'Offer updated successfully.')
            return redirect('admin_offer_list')
    else:
        form = OfferForm(instance=offer)
    context = {
        'form': form,
        'offer': offer,
        'edit': True,
        'categories': categories,
        'products': products,
        'selected_category_ids': offer.categories.values_list('id', flat=True),
        'selected_product_ids': offer.products.values_list('id', flat=True),
    }

    # selected_catefory_ids = offer.categories.values_list(
    #     'id', flat=True) if offer else []
    # selected_product_ids = offer.products.values_list(
    #     'id', flat=True) if offer else []
    # context = {
    #     'form': form,
    #     'edit': True,
    #     'offer': offer,
    #     'categories': categories,
    #     'products': products,
    #     'selected_category_ids': selected_catefory_ids,
    #     'selected_product_ids': selected_product_ids,
    # }
    return render(request, 'add_edit_offer.html', context)


@staff_member_required
def admin_delete_offer(request, offer_id):
    """
    to delete an existing offer
    """

    offer = get_object_or_404(Offer, id=offer_id)
    offer.delete()

    messages.success(request, "Offer deleted successfully.")
    return redirect('admin_offer_list')
