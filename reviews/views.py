from django.shortcuts import render, redirect, get_object_or_404
from .models import Review
from .forms import ReviewForm
from orders.models import OrderItem
from products.models import ProductVariant
from django.contrib.auth.decorators import login_required


@login_required
def submit_review(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product
    
    # Check if the user purchased this variant
    purchased = OrderItem.objects.filter(
        order__user=request.user,
        variant=variant,
        status='delivered',
        is_cancelled=False,
        is_returned=False
    ).exists()

    if not purchased:
        return redirect("detail_product", id=product.id)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product        
            review.save()
            return redirect("detail_product", id=product.id)

    else:
        form = ReviewForm()

    return render(request, "add_reviews.html", {"form": form, "variant": variant})
