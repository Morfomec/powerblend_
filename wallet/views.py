from django.shortcuts import render, redirect
from django.contrib import messages
from decimal import Decimal
from django.db.models import Sum
from .models import Wallet, WalletTransaction
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
# Create your views here.


@login_required
def wallet_detail(request):
    """
    to get the wallet details of user and if not create one
    """
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.order_by('-created_at')

    total_credits = wallet.transactions.filter(
        transaction_type='credit',
        status='success'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    total_debits = wallet.transactions.filter(
        transaction_type='debit',
        status='success'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    pending_counts = wallet.transactions.filter(status='pending').count()

    paginator = Paginator(transactions, 10)
    page_no = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_no)

    context = {
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'pending_counts': pending_counts,
    }

    return render(request, 'wallet_detail.html', context)


@login_required
def wallet_credit(request):

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))

        try:
            wallet.credit(amount)
            messages.success(request, f"₹{amount} added to your wallet!")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('wallet_detail')

    return render(request, 'wallet_credit.html', {'wallet': wallet})


@login_required
def wallet_debit(request):

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))

        try:
            wallet.debit(amount)
            messages.success(request, f"₹{amount} deducted from the wallet!")
        except ValueError as e:
            message.error(request, str(e))
        return redirect('wallet_detail')
    return render(request, 'wallet_debit.html', {'wallet': wallet})
