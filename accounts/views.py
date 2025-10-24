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

from .models import CustomUser, UserReferral
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from decimal import Decimal
from wallet.models import Wallet

from admin_app.utils import reward_referrer


# Create your views here.


def generate_otp():
    return str(random.randint(100000, 999999))



def register_view(request):
    """
    Handle user registration with optional referrer code.
    New users trigger wallet reward for referrer if code is valid.
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            # Step 1: Create and save new user (inactive until verified)
            user = form.save(commit=False)
            user.is_active = False
            user.is_verified = False
            user.save()

            # Step 2: Ensure the new user has a UserReferral object
            referrer_obj, created = UserReferral.objects.get_or_create(user=user)

            # Step 3: Handle optional referrer code
            ref_code = form.cleaned_data.get('referrer_code', '').strip().upper()
            if ref_code:
                try:
                    # Find referrer
                    referrer_ref = UserReferral.objects.get(referrer_code=ref_code)

                    # Link new user to the referrer
                    referrer_obj.referred_by = referrer_ref
                    referrer_obj.save()

                    # Credit ₹500 to referrer's wallet
                    wallet, w_created = Wallet.objects.get_or_create(user=referrer_ref.user)
                    wallet.credit(Decimal('500.00'))
                    print(f"DEBUG REFERRAL LINK: New User {user.email}, Referred By: {referrer_obj.referred_by}")

                    messages.success(
                        request,
                        f"Referral applied! {referrer_ref.user.full_name} earned ₹500 in their wallet."
                    )

                except UserReferral.DoesNotExist:
                    messages.warning(
                        request,
                        "Invalid referrer code — registration continued without it."
                    )

            # Step 4: Generate OTP for email verification
            otp = generate_otp()
            user.email_otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            # Step 5: Send OTP email
            send_mail(
                subject="Email Verification OTP",
                message=f"Hi {user.full_name},\n\nYour OTP is: {otp}",
                from_email="muhammedshifil@gmail.com",
                recipient_list=[user.email],
            )

            # Step 6: Store user_id in session for OTP verification
            request.session["user_id"] = user.id

            messages.success(
                request,
                "Registration successful! An OTP has been sent to your email. Verify your account within 5 minutes."
            )
            return redirect("verify_otp")

        else:
            messages.error(request, "Please correct the errors below.")
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
