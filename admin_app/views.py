from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.contrib.auth import get_user_model
from utils.pagination import get_pagination
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sessions.models import Session
from django.utils import timezone

User = get_user_model ()

# Create your views here.

# def admin_login(request):
#     # if request.user.is_authenticated:
#     #     # if request.user.is_staff or request.user.is_superuser:
#     #     return redirect('admin/dashboard')

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account has been blocked by admin.')
            elif user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'You are not an admin user.')
        else:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'admin_login.html')

@staff_member_required
def admin_dashboard(request):
    return render(request, 'dashboard.html', {'users' : request.user, 'active_page':'dashboard'})
    # return render(request, 'admin/dashboard.html', {'users' : request.user})
    
@login_required
def admin_logout(request):
    # logs out the user
    logout(request)
    # redirect to admin login page
    return redirect('admin_login')

@staff_member_required
def admin_user(request):
    # User = get_user_model()

    # to check if clear button clicked or not
    if 'clear' in request.GET:
        return redirect("admin_user") # Redirect back to the same view without any search parameters


    #query to exclude staffs and superusers
    users = User.objects.filter(is_superuser=False, is_staff=False).order_by('-date_joined')

    #to get query parameters
    search_query = request.GET.get("search", "").strip()
    filter_status = request.GET.get("filter", "")

    #search by name or email
    if search_query:
        users = users.filter(full_name__icontains=search_query) | users.filter(email__icontains=search_query)

    #filter by status
    if filter_status == "active":
        users = users.filter(is_active=True)
    elif filter_status == 'blocked':
        users = users.filter(is_active=False)

    #pagination
    page_obj = get_pagination(request, users, per_page=5)


    context = {
        'users': users,
        'page_obj': page_obj,
        'search_query': search_query,
        'filter_status': filter_status,
        "active_page": "users"
    }

    return render(request, 'user_management.html', context)
@staff_member_required
@login_required
def toggle_user_status(request, user_id):

    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()

    if not user.is_active:
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in sessions:
            data = session.get_decoded()
            session_user_id = data.get('_auth_user_id')
            if str(session_user_id) == str(user_id):
                session.delete()

        messages.success(request, f"{user.full_name} has been blocked and logged out.")
    else:
        messages.success(request, f"{user.full_name} has been unblocked and can log in now.")
    return redirect('admin_user')



@staff_member_required
def admin_settings(request):
    """
    Allow admin user to view and update their profile settings. 
    Pulling data directly from the the existing Customuser modeal.
    """

    #to get the current logged in staff user
    user = request.user

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        country = request.POST.get('country')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')

        #to update only if data is provided
        if full_name:
            user.full_name = full_name
        if email:
            user.email = email
        if mobile:
            user.mobile = mobile
        if country:
            user.country = country
        if date_of_birth :
            user.date_of_birth = date_of_birth
        if gender:
            user.gender = gender
        
        #to hnadle profile images
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']

        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('admin_dashboard')
    
    context = {
        'user': user,
    }

    return render(request, 'admin_settings.html', context)