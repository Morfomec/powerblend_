from django.shortcuts import render, redirect
from django.contrib import messages
from decimal  import Decimal
from .models import Wallet, WalletTransaction
from django.contrib.auth.decorators import login_required
# Create your views here.


@login_required
def wallet_detail(request):
    """
    to get the wallet details of user and if not create one
    """
    wallet,_ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.order_by('-created_at')

    context = {
        'wallet' : wallet,
        'transactions' : transactions,
    }

    return render(request, 'wallet_detail.html', context)

@login_required
def wallet_credit(request):

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        wallet,_ = Wallet.objects.get_or_create(user=request.user)

        try:
            wallet.credit(amount)
            messages.success(request, f"₹{amount} added to your wallet!")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('wallet_detail')
    return render(request, 'wallet_credit.html')

@login_required
def wallet_debit(request):
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        wallet,_ = Wallet.objects.get_or_create(user=request.user)

        try:
            wallet.debit(amount)
            messages.success(request, f"₹{amount} deducted from the wallet!")
        except ValueError as e:
            message.error(request, str(e))
        return redirect('wallet_detail')
    return render(request, 'wallet_debit.html')

