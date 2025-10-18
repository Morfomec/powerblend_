from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
    path("", views.checkout_view, name='checkout'),   
    path('paymenthandler/', views.paymenthandler, name='paymenthandler'),
    
]