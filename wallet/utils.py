from decimal import Decimal
from django.db import transaction
from .models import Wallet
from django.contrib import messages



# def refund_to_wallet(user, amount: Decimal, reason='Order/Item refund'):    
#     """
#     to credit amount back to users wallet on cancel or return items
#     """

#     if amount <= 0 :
#         return 

#     wallet,_ = Wallet.objects.get_or_create(user=user)
#     with transaction.atomic():
#         wallet.credit(amount, description=reason)
#         wallet.balance += amount
#         wallet.save(update_fields=['balance'])
#         wallet.transactions.create(amount=amount, transaction_type='credit', description=reason)


def refund_to_wallet(user, amount: Decimal, reason='Order/Item refund'):
    if amount <= 0:
        return

    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.credit(amount, description=reason)