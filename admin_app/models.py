from django.db import models
from django.conf import settings

# Create your models here.

# class AdminProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     profile_image = models.ImageField(upload_to='admin_profile_images/', default='default.png')
#     full_name