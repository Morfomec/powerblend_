from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Address
from .forms import AddressForm
# from .model import 

# Create your views here.

def user_profile_view(request):
    return render(request, 'user_profile_home.html')



@login_required
def address_view(request):
    """
    To view all the addresses
    """
    addresses = Address.objects.filter(user=request.user)
    context = {
        'addresses': addresses,
    }
    return render(request, 'address_listing.html', context)

@login_required
def address_create(request):
    """
    To create new addresses
    """
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            # to handle default address
            if request.POST.get('setDefault'):
                
                # to unset previous defaults for this user
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                address.is_default = True
            else: 
                address.is_default = False

            address.save()
            messages.success(request, "Address added successfully!")
            return redirect('address_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        # to prefill full name from Customuser 
        # form = AddressForm(initial={'full_name': request.user.full_name})
        form = AddressForm()
    
    context = {
        'form' : form,
        'is_update' : False,
    }
    return render(request, 'address_create.html')

@login_required
def address_delete(request, id):
    """
    To delete the addresses
    """
    address = get_object_or_404(Address, id=id, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted successfully!")
        return redirect("address_list")
    context = {
        'address': address,
    }
    return render(request, "addrees_listing.html", context)



@login_required
def address_update(request, id):
    """
    To delete the addresses
    """

    address = get_object_or_404(Address, id=id, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():

            address = form.save(commit=False)

             # Handle default address
            if request.POST.get('setDefault'):
                Address.objects.filter(user=request.user, is_default=True).exclude(pk=address.pk).update(is_default=False)
                address.is_default = True
            else:
                address.is_default = False


            address.save()
            messages.success(request,"Address updated successfully!")
            return redirect("address_list")
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'is_update':True,
        'address': address,
    }
    return render(request, "address_create.html", context)



@login_required
def address_set_default(request, id):

    address = get_object_or_404(Address, id=id, user=request.user)
    address.is_default = True
    address.save()
    return redirect('address_list')