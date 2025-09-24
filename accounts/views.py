from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from .forms import RegistrationForm

from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm

from .models import CustomUser
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random

# Create your views here.


def generate_otp():
    return str(random.randint(100000, 999999))


def register_view(request):
    """
    
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            # email = form.cleaned_data.get('email')

            # extra check to see if email already in db
            # if CustomUser.objects.filter(email=email).exists():
            #     messages.error(request, 'This email is already registered.')
            #     return redirect('register')

            # creating user but not activating
            user = form.save(commit=False)
            user.is_active = False
            user.is_verified = False

            # creating otp
            otp = generate_otp()
            user.email_otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            # sending otp via email
            send_mail(
                subject="Email Verifiaction OTP",
                message=f"Hi {user.full_name},\n\nYour OTP is: {otp}",
                from_email="muhammedshifil@gmail.com",
                recipient_list=[user.email],
            )

            # storing user_id in session for later otp verification
            request.session["user_id"] = user.id

            # return redirect('login')
            messages.success(
                request,
                "Registration is successful!! An OTP has been sent to your email. Verify account within 5 minutes.",
            )
            return redirect("verify_otp")
        else:
            messages.error(request, "Please corrects the errors below.")
            return render(request, "registration.html", {"form": form})

    else:
        form = RegistrationForm()

    return render(request, "registration.html", {"form": form})


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect("home")
        else:
            messages.error(request, "Invalid credentials!!")
            return redirect("login")
    return render(request, "login.html")


# @never_cache
# @login_required(login_url='login')
# def home_view(request):
#     return render(request, "home.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You are logged out")
    return redirect("home")


def forgot_password(request):
    return render(request, "password_reset.html")


class CustomPasswordChangeView(PasswordChangeView):
    form_class = PasswordChangeForm
    template_name = "password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

    def form_valid(self, form):
        messages.success(self.request, "Your password was successfully updated!")
        return super().form_valid(form)


@never_cache
def verify_otp_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Session expired. Please register again.")
        return redirect("register")

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found. Please register first.")
        return redirect("register")

    if request.method == "POST":
        otp_input = request.POST.get("otp")

        # to check otp is expired or not
        if not user.otp_created_at or (
            user.otp_created_at + timedelta(minutes=5) < timezone.now()
        ):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("verify_otp")

        if otp_input == user.email_otp:
            user.is_active = True
            user.is_verified = True
            user.email_otp = ""
            user.otp_created_at = None
            user.save()

            del request.session["user_id"]

            messages.success(
                request, "Email verified successfully! You can now log in."
            )
            return redirect("login")
        else:
            messages.error(
                request, "Invalid OTP. Please check your email and try again."
            )
            return redirect("verify_otp")

    return render(request, "verify_otp.html")


@never_cache
def resend_otp(request):
    user_id = request.session.get("user_id")
    if not user_id:
        # messages.error(request, 'Session expired. Please register again.')
        return redirect("register")

    user = CustomUser.objects.get(id=user_id)
    otp = generate_otp()
    user.email_otp = otp
    user.otp_created_at = timezone.now()
    user.save()

    send_mail(
        subject="New OTP for Email Verofocation",
        message=f"Hi {user.full_name},\n\nYour new OTP is {otp}",
        from_email="muhammedshifil@gmail.com",
        recipient_list=[user.email],
    )

    messages.success(
        request,
        "A new OTP has been sent to your email. Please verify your account within 5 minutes.",
    )
    return redirect("verify_otp")
