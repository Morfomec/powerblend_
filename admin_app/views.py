from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.contrib.auth import get_user_model
from utils.pagination import get_pagination

User = get_user_model ()

# Create your views here.

def admin_login(request):
    # if request.user.is_authenticated:
    #     # if request.user.is_staff or request.user.is_superuser:
    #     return redirect('admin/dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            # messages.success(request, 'Logged in syuccessfully')
            return redirect('admin_dashboard')
        else:
            messages.error(request, ' Invalid credentials or not an admin user.')
    return render(request, 'admin_login.html')

@login_required
def admin_dashboard(request):
    return render(request, 'dashboard.html', {'users' : request.user, 'active_page':'dashboard'})
    # return render(request, 'admin/dashboard.html', {'users' : request.user})
    

def admin_logout(request):
    # logs out the user
    logout(request)
    # redirect to admin login page
    return redirect('admin_login')

@login_required
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
    page_obj = get_pagination(request, users, per_page=1)


    context = {
        'users': users,
        'page_obj': page_obj,
        'search_query': search_query,
        'filter_status': filter_status,
        "active_page": "users"
    }

    return render(request, 'user_management.html', context)


def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect('admin_user')

