from decimal import Decimal
from django.db import transaction
from .models import Wallet
from django.contrib import messages



def refund_to_wallet(user, amount: Decimal, reason='Order/Item refund'):
    if amount <= 0:
        return

    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.credit(amount, description=reason)