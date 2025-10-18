from django.urls import path
from . import views


urlpatterns = [
    path('', views.wallet_detail, name='wallet_detail'),
    path('credit/', views.wallet_credit, name='wallet_credit'),
    path('debit/', views.wallet_debit, name='wallet_debit'),
]