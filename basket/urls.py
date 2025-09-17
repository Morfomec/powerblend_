from django.urls import path
from . import views


urlpatterns=[
    path("", views.BasketDetailView.as_view(), name='basket'),
    path("add/<int:product_id>/", views.BasketAddView.as_view(), name="add"),
    path("remove/<int:product_id>/", views.BasketRemoveView.as_view(), name="remove"),
    
]
