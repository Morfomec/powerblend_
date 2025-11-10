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
from django.db.models import Sum, Count, F
from datetime import date, timedelta
from orders.models import Order
from .models import Coupon, Banner
from django.core.paginator import Paginator

from accounts.models import CustomUser
from products.models import Product
from category.models import Category

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from openpyxl import Workbook
from django.utils.dateparse import parse_date

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from .forms import CouponForm, BannerForm
from django.db.models.functions import TruncMonth, TruncDate
import json
from django.shortcuts import render


User = get_user_model ()

# Create your views here.



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

    # Basic Stats

    total_users = CustomUser.objects.count()
    total_orders = Order.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()

 
    # Top Selling Products 

    products_page = request.GET.get('products_page', 1)
    top_products_queryset = Product.objects.annotate(
        total_quantity_sold=Sum('variants__orderitems__quantity'),
        total_revenue=Sum(F('variants__orderitems__quantity') * F('variants__orderitems__price')),
        order_count=Count('variants__orderitems__id', distinct=True)
    ).filter(
        total_quantity_sold__isnull=False
    ).order_by('-total_quantity_sold')

    products_paginator = Paginator(top_products_queryset, 10)
    top_products = products_paginator.get_page(products_page)


    # Top Selling Categories (Paginated)

    categories_page = request.GET.get('categories_page', 1)
    top_categories_queryset = Category.objects.annotate(
        total_quantity_sold=Sum('products__variants__orderitems__quantity'),
        total_revenue=Sum(F('products__variants__orderitems__quantity') * F('products__variants__orderitems__price')),
        order_count=Count('products__variants__orderitems__id', distinct=True)
    ).filter(
        total_quantity_sold__isnull=False
    ).order_by('-total_quantity_sold')

    categories_paginator = Paginator(top_categories_queryset, 10)
    top_categories = categories_paginator.get_page(categories_page)


    # Chart Data 

    filter_type = request.GET.get('filter', 'weekly')  # default to weekly
    today = timezone.now().date()

    date_list = []
    chart_labels = []

    if filter_type == 'daily':
        last_days = 7
        date_list = [today - timedelta(days=i) for i in range(last_days - 1, -1, -1)]
        chart_labels = [d.strftime('%b %d') for d in date_list]

    elif filter_type == 'weekly':
        weeks = 8
        date_list = [today - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
        chart_labels = [f"Week {d.isocalendar().week}" for d in date_list]

    elif filter_type == 'monthly':
        months = 6
        date_list = [today.replace(day=1) - timedelta(days=30 * i) for i in range(months - 1, -1, -1)]
        chart_labels = [d.strftime('%b %Y') for d in date_list]

    elif filter_type == 'yearly':
        years = 5
        date_list = [today.replace(month=1, day=1).replace(year=today.year - i) for i in range(years - 1, -1, -1)]
        chart_labels = [str(d.year) for d in date_list]

    else:
        # fallback = last 7 days
        last_days = 7
        date_list = [today - timedelta(days=i) for i in range(last_days - 1, -1, -1)]
        chart_labels = [d.strftime('%b %d') for d in date_list]

    chart_total_sales = []
    chart_total_users = []

    # Generate chart data according to filter_type
    for i, d in enumerate(date_list):
        if filter_type == 'daily':
            next_d = d
            total_sales = Order.objects.filter(created_at__date=next_d).aggregate(total=Sum('total'))['total'] or 0
            user_count = CustomUser.objects.filter(date_joined__date=next_d).count()

        elif filter_type == 'weekly':
            start = d - timedelta(days=d.weekday())  # Monday of that week
            end = start + timedelta(days=6)
            total_sales = Order.objects.filter(created_at__date__range=[start, end]).aggregate(total=Sum('total'))['total'] or 0
            user_count = CustomUser.objects.filter(date_joined__date__range=[start, end]).count()

        elif filter_type == 'monthly':
            start = d.replace(day=1)
            # end of month
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
            total_sales = Order.objects.filter(created_at__date__range=[start, end]).aggregate(total=Sum('total'))['total'] or 0
            user_count = CustomUser.objects.filter(date_joined__date__range=[start, end]).count()

        elif filter_type == 'yearly':
            start = d.replace(month=1, day=1)
            end = start.replace(year=start.year + 1) - timedelta(days=1)
            total_sales = Order.objects.filter(created_at__date__range=[start, end]).aggregate(total=Sum('total'))['total'] or 0
            user_count = CustomUser.objects.filter(date_joined__date__range=[start, end]).count()

        else:
            total_sales = 0
            user_count = 0

        chart_total_sales.append(float(total_sales))
        chart_total_users.append(user_count)

    # ---------------------------
    # CONTEXT
    # ---------------------------
    context = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_categories': total_categories,
        'users': request.user,
        'active_page': 'dashboard',

        'top_products': top_products,
        'top_categories': top_categories,

        # Chart data (for Chart.js)
        'chart_labels': json.dumps(chart_labels),
        'chart_total_sales': json.dumps(chart_total_sales),
        'chart_total_users': json.dumps(chart_total_users),

        # Current chart filter
        'filter_type': filter_type,
    }

    return render(request, 'dashboard.html', context)



    
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
        return redirect("admin_user") 


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




@staff_member_required
def sales_report(request):
    filter_type = request.GET.get('filter')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    orders = Order.objects.filter() 

    if filter_type == 'daily':
        orders = orders.filter(created_at__date=today)
    elif filter_type == 'weekly':
        week_ago = today - timedelta(days=7)
        orders = orders.filter(created_at__date__range=[week_ago, today])
    elif filter_type == 'monthly':
        month_ago = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_ago)
    elif filter_type == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    total_sales = orders.aggregate(total_amount=Sum('total'))['total_amount'] or 0
    total_discount = orders.aggregate(total_amount=Sum('discount_amount'))['total_amount'] or 0
    total_coupon = orders.aggregate(total_coupon=Sum('coupon_discount'))['total_coupon'] or 0
    total_orders = orders.count()


    orders = orders.order_by('-created_at')


  
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    context = {
        'orders': orders,
        'total_sales': total_sales,
        'total_discount': total_discount,
        'total_coupon': total_coupon,
        'total_orders': total_orders,
        'filter_type': filter_type,
    }
    return render(request, 'sales_report.html', context)

@staff_member_required
def download_pdf(request):
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    orders = Order.objects.filter()

    # Apply filters
    if filter_type == 'daily':
        orders = orders.filter(created_at__date=today)
    elif filter_type == 'weekly':
        week_ago = today - timedelta(days=7)
        orders = orders.filter(created_at__date__range=[week_ago, today])
    elif filter_type == 'monthly':
        month_ago = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_ago)
    elif filter_type == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
    # else: all orders already included

    # PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{filter_type or "all"}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph(f"Sales Report - {filter_type.capitalize() if filter_type else 'All'}", styles['Title']))
    elements.append(Paragraph("Generated by POWERBLEND Admin Panel", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Table header
    data = [["S.No", "Order ID", "Customer", "Total", "Discount", "Date"]]
    total_sales = 0
    total_discount = 0

    for idx, order in enumerate(orders, start=1):
        data.append([
            str(idx),
            str(order.id),
            str(order.user),
            f"{order.total:.2f}",
            f"{order.discount_amount:.2f}",
            order.created_at.strftime("%Y-%m-%d")
        ])
        total_sales += order.total
        total_discount += order.discount_amount

        # Add page break every 40 rows (adjust as needed)
        if idx % 40 == 0:
            table = Table(data, colWidths=[40, 70, 150, 70, 70, 70])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(PageBreak())
            data = [["S.No", "Order ID", "Customer", "Total", "Discount", "Date"]] 

    # Add totals row
    data.append([
        "",
        "",
        "Totals",
        f"{total_sales:.2f}",
        f"{total_discount:.2f}",
        ""
    ])

    # Final table
    table = Table(data, colWidths=[40, 70, 150, 70, 70, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightyellow),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(table)

    doc.build(elements)
    return response


@staff_member_required
def download_excel(request):
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    orders = Order.objects.filter()

    # Apply filters
    if filter_type == 'daily':
        orders = orders.filter(created_at__date=today)
    elif filter_type == 'weekly':
        week_ago = today - timedelta(days=7)
        orders = orders.filter(created_at__date__range=[week_ago, today])
    elif filter_type == 'monthly':
        month_ago = today.replace(day=1)
        orders = orders.filter(created_at__date__gte=month_ago)
    elif filter_type == 'custom' and start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start and end:
            orders = orders.filter(created_at__date__range=[start, end])

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    # Headers
    ws.append(['S.No', 'Order No', 'Customer', 'Date', 'Total', 'Discount', 'Coupon'])

    orders = orders.order_by('-created_at')  

    # Then loop over orders as before
    for idx, order in enumerate(orders, start=1):
        ws.append([
            idx,
            f"ORD-{order.id:04d}",
            getattr(order.user, 'full_name', str(order.user)),
            order.created_at.strftime("%Y-%m-%d"),
            order.total,
            order.discount_amount,
            order.coupon_discount,
        ])
    # Prepare response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{filter_type or "all"}.xlsx"'
    wb.save(response)
    return response



@staff_member_required
def coupon_list(request):
    coupons = Coupon.objects.all().order_by('-created_at')
    context = {
        'coupons':coupons,
    }
    return render(request, 'coupon_list.html', context)

@staff_member_required
def add_coupon(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Coupon created successfully!')
            return redirect('coupon_list')
        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = CouponForm()

    context = {
        'form' : form,
    }
    return render(request, 'add_coupon.html', context)


@staff_member_required
def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    messages.success(request, f"Coupon '{coupon.code}' deleted successfully.")
    return redirect('coupon_list')


@staff_member_required
def admin_banner_list(request):
    """
    Display list of all banners for admin
    """
    banner = Banner.objects.all().order_by('-created_at')
    
    context = {
        'banner': banner,
    }
    return render(request, 'banner_list.html', context)


@staff_member_required
def admin_banner_add(request):
    """
    Add new banner - handles both modal and standalone page
    """
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES) 
        
        if form.is_valid():
            form.save()
            messages.success(request, "Banner successfully added!", extra_tags='success')
            return redirect('admin_banner_list')
        else:
            messages.error(request, "Please correct the errors below.", extra_tags='danger')
    else:
        form = BannerForm()
    
    # For modal: redirect back to list with form errors
    # For standalone: render add page
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request from modal
        return redirect('admin_banner_list')
    
    context = {
        'form': form,
    }
    return render(request, 'banner_list.html', context)


@staff_member_required
def admin_banner_edit(request, banner_id):
    """
    Edit existing banner
    """
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner updated successfully!', extra_tags='success')
            return redirect('admin_banner_list')
        else:
            messages.error(request, "Please correct the errors below.", extra_tags='danger')
    else:
        form = BannerForm(instance=banner)

    context = {
        'form': form,
        'banner': banner,
    }
    return render(request, 'banner_list.html', context)


@staff_member_required
def admin_banner_delete(request, banner_id):
    """
    Delete banner
    """
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'POST':
        banner_title = banner.title or 'Banner'
        banner.delete()
        messages.success(request, f'"{banner_title}" deleted successfully!', extra_tags='success')
    
    return redirect('admin_banner_list')




def handler400(request, exception=None):
    """Handle 400 Bad Request errors"""
    context = {'error_code': 400}
    return render(request, 'error.html', context, status=400)

def handler403(request, exception=None):
    """Handle 403 Forbidden errors"""
    context = {'error_code': 403}
    return render(request, 'error.html', context, status=403)

def handler404(request, exception=None):
    """Handle 404 Not Found errors"""
    context = {'error_code': 404}
    return render(request, 'error.html', context, status=404)

def handler500(request):
    """Handle 500 Internal Server Error"""
    context = {'error_code': 500}
    return render(request, 'error.html', context, status=500)