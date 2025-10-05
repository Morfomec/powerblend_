from django.db.models import F 

# Increment stock(when cancelling or returning)
def increment_stock(variant, qty):
    variant.stock = F ('stock') + qty
    variant.save(update_fields= ['stock'])
    variant.refresh_from_db()


#decrement stock when placing an order
def decrement_stock(variant, qty):
    variant.stock = F('stock') - qty
    variant.save(update_fields=['stock'])