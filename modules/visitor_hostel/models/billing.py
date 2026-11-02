from django.db import models
from decimal import Decimal
from .booking import BookingDetail

class Bill(models.Model):
    SETTLEMENT_CHOICES = [('Pending', 'Pending'), ('Settled', 'Settled')]

    bill_number = models.CharField(max_length=32, unique=True)
    booking = models.OneToOneField(BookingDetail, on_delete=models.CASCADE, related_name="bill")
    room_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    meal_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    cancellation_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_mode = models.CharField(max_length=20, default='Cash')
    settlement_status = models.CharField(max_length=20, choices=SETTLEMENT_CHOICES, default='Pending')
    settled_at = models.DateTimeField(null=True, blank=True)
    settled_by = models.CharField(max_length=100, blank=True, null=True)
    is_immutable = models.BooleanField(default=False)

    class Meta:
        db_table = "vh_bill"
        ordering = ["-bill_number"]

    def __str__(self):
        return f"Bill {self.bill_number}: {self.total_amount} ({self.settlement_status})"
