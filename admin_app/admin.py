from django.contrib import admin
from .models import Banner

# Register your models here.
@admin.register(Banner)
class Banner(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_field = ('title')