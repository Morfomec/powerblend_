from django.apps import AppConfig


class AdminAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_app"


class CouponsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "coupons"
