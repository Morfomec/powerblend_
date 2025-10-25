from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.contrib.auth import update_session_auth_hash

from .models import Address
from .forms import AddressForm
from django.urls import reverse

from .forms import EditProfileForm, EmailChangeForm

from accounts.models import UserReferral

# from .model import 

# Create your views here.

@login_required
def user_profile_view(request):
    return render(request, 'user_profile_home.html')



@login_required
def user_dashboard(request):
    """
    show user profile, addresses and recent orders.
    """

    user = request.user
    addresses = Address.objects.filter(user=request.user)

    referral, created = UserReferral.objects.get_or_create(user=user)

    if created and not referral.referral_code:
        referral.save()
    
    referral.refresh_from_db() 

    referred_users = referral.referrers.all()

    context = {
        'user': user,
        'addresses' : addresses,
        'referral_code': referral.referral_code,
        'referred_users' : referred_users,
        # 'orders': orders,
    }

    return render(request, 'user_dashboard.html', context)



@login_required
def edit_profile(request):
    """
    Edit user profile
    """

    user = request.user

    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("user_dashboard")
    
    else:
        form = EditProfileForm(instance=request.user)

    context ={
        'form' : form,
    }
    return render(request, "edit_profile.html", context)


@login_required
def change_email(request):
    """
    Change email with OTP verification
    """

    user = request.user
    # if request.method == 'POST':
    #     form = EditProfileForm(request.POST, request.FILES, instance=request.user)
    # else: 
    #     form = EditProfileForm(instance=request.user)

    otp_sent = request.session.get('otp_sent', False)
    new_email = request.session.get('new_email', '')

    if request.method == 'POST':
        form = EmailChangeForm(request.POST)
        entered_otp = request.POST.get('email_otp')

        if entered_otp:
            session_otp = request.session.get('email_otp')
            if entered_otp == session_otp:
                user.email = request.session.get('new_email')
                user.save()

                request.session.pop('email_otp', None)
                request.session.pop('new_email', None)
                request.session.pop('otp_sent', None)

                messages.success(request, "Email updated successfully.")
                return redirect('change_email')
            else:
                messages.error(request, "Invalid OTP. Please try again.")
                otp_sent = True

        elif form.is_valid():
            new_email = form.cleaned_data['new_email']
            otp = get_random_string(length=6, allowed_chars='0123456789')

            request.session['email_otp'] = otp
            request.session['new_email'] = new_email
            request.session['otp_sent'] = True


            # sending otp via email
            send_mail(
                subject="Email Verifiaction OTP",
                message=f"Hi {user.full_name},\n\nYour OTP to update email is: {otp}",
                from_email="muhammedshifil@gmail.com",
                recipient_list=[user.email],
                fail_silently = False,
            )
            messages.info(request, "An OTP has been sent to your current email. Please verify to proceed.")
            return redirect('change_email')
    else:
        form = EmailChangeForm(initial={'email': user.email})
    
    context = {
        'form' : form,
        'otp_sent' : otp_sent,
    }
    return render(request, 'change_email.html', context)


@login_required
def verify_email_otp(request):
    """
    verify OTP sent to new email
    """

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        if otp_entered == request.session.get('email_otp'):
            request.user.email = request.session.get('new_email')
            request.user.save()
            messages.success(request, "Email updated successfully.")

            # clear session
            request.session.pop('email_otp')
            request.session.pop('new_email')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid OTP.')
    return render(request, 'verify_email.otp.html')


@login_required
def change_password(request):
    """
    Changing password for the account
    """

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data = request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('edit_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(user=request.user)
    context = {
        'form' : form,
    }
    return render(request, 'change_password.html', context)


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
            next_url = request.POST.get("next") or request.GET.get("next") or reverse("address_list")
            messages.success(request,"Address updated successfully!")
            return redirect(next_url)
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'is_update':True,
        'address': address,
        'next': request.GET.get("next",""),
    }
    return render(request, "address_create.html", context)



@login_required
def address_set_default(request, id):

    address = get_object_or_404(Address, id=id, user=request.user)
    address.is_default = True
    address.save()
    return redirect('address_list')

