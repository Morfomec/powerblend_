from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.crypto import get_random_string
# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **kwargs):
        
        if not email:
            raise ValueError("Email is required")
        if not full_name:
            raise ValueError("Full name is required")

        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **kwargs):
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)
        kwargs.setdefault("is_active", True)


        if kwargs.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if kwargs.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email=email, full_name=full_name, password=password, **kwargs)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    profile_image = models.ImageField(upload_to='user_profile_images/', blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('Male','Male'),('Female','Female'),('Other','Other')], blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True, default=timezone.now)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    # Required fields for PermissionsMixin, with unique related_name
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups', # A unique related_name
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions', # A unique related_name
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    # for OTP verification
    is_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        if self.full_name:
            return str(self.full_name)
        return str(self.email)

    class Meta:
        db_table = 'registered_users'


def generate_referral_code(length=8):
    return get_random_string(length).upper()


class UserReferral(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='referral')
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_users')
    reward_given = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user.full_name or self.user.email} - {self.referral_code}"


    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
            
            
        super().save(*args, **kwargs)