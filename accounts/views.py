from django.shortcuts import render, redirect,get_object_or_404
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



# def register_view(request):
#     """
#     Handle user registration with optional referrer code.
#     New users trigger wallet reward for referrer if code is valid.
#     """
#     if request.method == "POST":
#         form = RegistrationForm(request.POST)

#         if form.is_valid():

#             ref_code = form.cleaned_data.get('referrer_code', '').strip().upper()
            
#             referrer_ref = None

#             if ref_code:
#                 try:
#                     referrer_ref = UserReferral.objects.get(referral_code=ref_code)
#                 except UserReferral.DoesNotExist:
#                     messages.error(request, "Invalid referral code. Please try again.")
#                     return render(request, "registration.html", {"form" : form})


#             # Step 1: Create and save new user (inactive until verified)
#             user = form.save(commit=False)
#             user.is_active = False
#             user.is_verified = False
#             user.save()

#             # Step 2: Create referral record for new user
#             referral_obj, _ = UserReferral.objects.get_or_create(user=user)

#             # Step 3: Link new user to the referrer (if valid)
#             if referrer_ref:
#                 referral_obj.referred_by = referrer_ref
#                 referral_obj.save()  

#                 messages.success(
#                     request,
#                     f"Referral applied! {referrer_ref.user.full_name} will earn ₹500 after your registration."
#                 )

#             # Step 4: Generate OTP for email verification
#             otp = generate_otp()
#             user.email_otp = otp
#             user.otp_created_at = timezone.now()
#             user.save()

#             # Step 5: Send OTP email
#             send_mail(
#                 subject="Email Verification OTP",
#                 message=f"Hi {user.full_name},\n\nYour OTP is: {otp}",
#                 from_email="muhammedshifil@gmail.com",
#                 recipient_list=[user.email],
#             )

#             # Step 6: Store user_id in session for OTP verification
#             request.session["user_id"] = user.id

#             messages.success(
#                 request,
#                 "Registration successful! An OTP has been sent to your email. Verify your account within 5 minutes."
#             )
#             return redirect("verify_otp")

#         else:
#             messages.error(request, "Please correct the errors below.")
#             return render(request, "registration.html", {"form": form})

#     else:
#         form = RegistrationForm()

#     return render(request, "registration.html", {"form": form})


def register_view(request):
    """
    Handle user registration with optional referrer code.
    Wallet credit is only applied if the referrer code is valid.
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            ref_code = form.cleaned_data.get('referrer_code', '').strip().upper()
            referrer_ref = None

            # Optional referral
            if ref_code:
                try:
                    referrer_ref = UserReferral.objects.get(referral_code=ref_code)
                except UserReferral.DoesNotExist:
                    messages.warning(request, "Invalid referral code. Registration will continue without it.")

            # Create user (inactive)
            user = form.save(commit=False)
            user.is_active = False
            user.is_verified = False
            user.save()

            # Create referral record for new user
            referral_obj, _ = UserReferral.objects.get_or_create(user=user)

            # Link to referrer if valid
            if referrer_ref:
                referral_obj.referred_by = referrer_ref
                referral_obj.reward_given = False
                referral_obj.save()
                messages.success(
                    request,
                    f"Referral applied! {referrer_ref.user.full_name} will earn ₹500 after your registration."
                )

            # Generate OTP
            otp = generate_otp()
            user.email_otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            # Send OTP email
            send_mail(
                subject="Email Verification OTP",
                message=f"Hi {user.full_name},\n\nYour OTP is: {otp}",
                from_email="muhammedshifil@gmail.com",
                recipient_list=[user.email],
            )

            # Store user_id in session for OTP verification
            request.session["user_id"] = user.id
            messages.success(request, "Registration successful! An OTP has been sent to your email.")
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
            messages.success(request, "Logged in successfully!", extra_tags='logged_successfully')
            return redirect("home")
        else:
            messages.error(request, "Invalid credentials!!", extra_tags='invalid_credentials')
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


# @never_cache
# def verify_otp_view(request):
#     user_id = request.session.get("user_id")
#     if not user_id:
#         messages.error(request, "Session expired. Please register again.")
#         return redirect("register")

#     try:
#         user = CustomUser.objects.get(id=user_id)
#     except CustomUser.DoesNotExist:
#         messages.error(request, "User not found. Please register first.")
#         return redirect("register")

#     if request.method == "POST":
#         otp_input = request.POST.get("otp")

#         # to check otp is expired or not
#         if not user.otp_created_at or (
#             user.otp_created_at + timedelta(minutes=5) < timezone.now()
#         ):
#             messages.error(request, "OTP has expired. Please request a new one.")
#             return redirect("verify_otp")

#         if otp_input == user.email_otp:
#             user.is_active = True
#             user.is_verified = True
#             user.email_otp = ""
#             user.otp_created_at = None
#             user.save()


#             try:
#                 referral = UserReferral.objects.get(user=user)
#                 if referral.referred_by:
#                     referrer_user = referral.referred_by.user
#                     wallet, _ = Wallet.objects.get_or_create(user=referrer_user)
#                     wallet.credit(Decimal('500.00'))
#                     referral.reward_given = True
#                     referral.save()
#                     messages.success(request, f"₹500 credited to {referrer_user.full_name}'s wallet for referring you!")
#             except UserReferral.DoesNotExist:
#                 pass        

#             del request.session["user_id"]

#             messages.success(
#                 request, "Email verified successfully! You can now log in."
#             )
#             return redirect("login")
#         else:
#             messages.error(
#                 request, "Invalid OTP. Please check your email and try again."
#             )
#             return redirect("verify_otp")

#     return render(request, "verify_otp.html")



@never_cache
def verify_otp_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Session expired. Please register again.")
        return redirect("register")

    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        otp_input = request.POST.get("otp")

        if not user.otp_created_at or user.otp_created_at + timedelta(minutes=5) < timezone.now():
            messages.error(request, "OTP expired. Please register again.")
            return redirect("register")

        if otp_input == user.email_otp:
            user.is_active = True
            user.is_verified = True
            user.email_otp = ""
            user.otp_created_at = None
            user.save()

            # Credit wallet if valid referral exists and reward not yet given
            try:
                referral = UserReferral.objects.get(user=user)
                if referral.referred_by and not referral.reward_given:
                    wallet, _ = Wallet.objects.get_or_create(user=referral.referred_by.user)
                    wallet.credit(Decimal('500.00'))
                    referral.reward_given = True
                    referral.save()
                    messages.success(request,f"₹500 credited to {referral.referred_by.user.full_name}'s wallet for referring you!")
            except UserReferral.DoesNotExist:
                pass

            del request.session["user_id"]
            messages.success(request, "Email verified successfully! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Invalid OTP. Please try again.")

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


def account_inactive(request):
    """
    Render the custom 'Account Inactive' page.
    """
    return render(request, "account_inactive_custom.html")