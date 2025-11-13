from django.contrib import admin
from .models import CustomUser

# Register your models here.
@admin.register(CustomUser)
class CustomUser(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'is_active', 'is_staff', 'is_verified')

