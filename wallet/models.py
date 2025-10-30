from django.db import models, transaction
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from orders.models import Order

# Create your models here.


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name}'s Wallet: ₹{self.balance}"

    def credit(self, amount: Decimal, description="Amount added to wallet", order=None):
        """
        add money to wallet and record transcation
        """
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")
        with transaction.atomic():
            WalletTransaction.objects.create(wallet=self, amount=amount, transaction_type='Credit', description=description, order=order)
            self.balance += amount
            self.save(update_fields=['balance'])

    
    def debit(self, amount: Decimal, description="Payment from wallet", order=None):
        """
        deduct money if enough balance and record the transitions
        """
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")
        if self.balance < amount:
            raise ValueError("Insufficient wallet balance")
        with transaction.atomic():
            WalletTransaction.objects.create(wallet=self, amount=amount, transaction_type='Debit', description=description, order=order)
            self.balance -= amount
            self.save(update_fields=['balance'])

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=[('credit', 'Credit'), ('debit', 'Debit')])
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.description:
            self.description= ("Amount added to wallet" if self.transaction_type == 'credit' else "Amount debited from wallet")
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.transaction_type} of {self.amount} for {self.wallet.user.full_name}"