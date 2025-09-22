from django.contrib import admin
from . models import Product, ProductImage, ProductVariant, Flavor, Weight

# Register your models here.

# admin.site.register(Product)
# admin.site.register(ProductImage)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2
    fields = ["images", "caption", "is_primary"]
    readonly_fields = ["image_preview"]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="hegiht: 100px;"/>', obj.image.url)
        return "-"

    image_preview.short_description = "preview"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ["flavor", "weight", "price", "stock"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariantInline]
    list_display = [ "name", "category", "is_listed", "created_at", "updated_at"]
    list_filter = ["category", "is_listed", "created_at"]
    search_field = ["name", "description"]
    prepopulated_field = {"slug": ("name",)}
    ordering = ["-created_at"]


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display = ["flavor"]
    search_fields = ["flavor"]

@admin.register(Weight)
class WeightAdmin(admin.ModelAdmin):
    list_display = ["weight"]
    search_fields = ["weight"]