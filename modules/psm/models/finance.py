# Vendor invoices and append-only payment transactions (CFR-PSM-013, BR-PSM-017, 018, 022).
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.psm.domain import state_machine as sm


class Invoice(TimeStampedModel):
    STATUS = [(s, s.replace("_", " ").title()) for s in sm.INVOICE_STATES]

    invoice_number = models.CharField(max_length=64)
    purchase_order = models.ForeignKey(
        "PurchaseOrder", on_delete=models.PROTECT, related_name="invoices"
    )
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="invoices")
    billed_quantity = models.PositiveIntegerField()
    billed_amount = models.DecimalField(max_digits=14, decimal_places=2)
    eligible_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS, default=sm.INV_SUBMITTED)
    hold_reason = models.TextField(blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    submitted_by_user_id = models.IntegerField()

    class Meta:
        db_table = "psm_invoice"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "invoice_number"], name="psm_invoice_vendor_number_unique"
            ),
            models.CheckConstraint(
                condition=Q(billed_quantity__gt=0) & Q(billed_amount__gt=0),
                name="psm_invoice_amounts_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_invoice_status_idx"),
        ]


class PaymentTransaction(models.Model):
    """Append-only payment ledger; corrections are reversing entries, never mutations."""

    STATUS = [("released", "Released"), ("reversed", "Reversed")]

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_reference = models.CharField(max_length=64, unique=True)
    is_partial = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=STATUS, default="released")
    processed_by_user_id = models.IntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_payment_transaction"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="psm_payment_amount_positive"),
        ]
        indexes = [
            models.Index(fields=["invoice", "-created_at"], name="psm_payment_invoice_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.payment_reference} ({self.amount})"
