# Stock items, locations, append-only ledger, reservations, and transfers (BR-PSM-003, 013, 027).
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class StockItem(TimeStampedModel):
    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True)
    unit = models.CharField(max_length=32, default="unit")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "psm_stock_item"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="psm_stock_item_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sku} {self.name}"


class StockLocation(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    department = models.CharField(max_length=64)
    is_central = models.BooleanField(default=False)

    class Meta:
        db_table = "psm_stock_location"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["department", "is_central"], name="psm_stock_loc_dept_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.department})"


class StockLedgerEntry(models.Model):
    """Append-only inventory ledger; corrections are reversing entries, never edits."""

    ENTRY_TYPES = [
        ("opening", "Opening Balance"),
        ("receipt_post", "Accepted Receipt Posting"),
        ("internal_issue_post", "Internal Issue Posting"),
        ("transfer_out", "Transfer Out"),
        ("transfer_in", "Transfer In"),
        ("adjustment", "Authorized Adjustment"),
    ]

    item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="ledger_entries")
    location = models.ForeignKey(
        StockLocation, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=24, choices=ENTRY_TYPES)
    quantity_delta = models.IntegerField()
    source_ref_type = models.CharField(max_length=32, blank=True)
    source_ref_id = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=300)
    actor_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_stock_ledger"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(quantity_delta=0), name="psm_ledger_nonzero_delta"),
        ]
        indexes = [
            models.Index(
                fields=["item", "location", "-created_at"], name="psm_ledger_item_loc_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"ledger#{self.pk} {self.entry_type} {self.quantity_delta:+d}"


class StockReservation(TimeStampedModel):
    PURPOSE = [("internal_issue", "Internal Issue"), ("stock_transfer", "Stock Transfer")]
    STATUS = [("active", "Active"), ("consumed", "Consumed"), ("released", "Released")]

    item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="reservations")
    location = models.ForeignKey(
        StockLocation, on_delete=models.PROTECT, related_name="reservations"
    )
    quantity = models.PositiveIntegerField()
    purpose = models.CharField(max_length=24, choices=PURPOSE)
    indent_id = models.IntegerField(null=True, blank=True)
    transfer_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="active")
    reserved_by_user_id = models.IntegerField()
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_stock_reservation"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="psm_reservation_qty_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["item", "location", "status"], name="psm_reservation_active_idx"),
        ]


class StockTransfer(TimeStampedModel):
    STATUS = [
        ("requested", "Requested"),
        ("dispatched", "Dispatched"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    transfer_number = models.CharField(max_length=32, unique=True)
    item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="transfers")
    source_location = models.ForeignKey(
        StockLocation, on_delete=models.PROTECT, related_name="outgoing_transfers"
    )
    destination_location = models.ForeignKey(
        StockLocation, on_delete=models.PROTECT, related_name="incoming_transfers"
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=STATUS, default="requested")
    reservation = models.ForeignKey(
        StockReservation, on_delete=models.PROTECT, null=True, blank=True, related_name="transfers"
    )
    requested_by_user_id = models.IntegerField()
    dispatched_by_user_id = models.IntegerField(null=True, blank=True)
    confirmed_by_user_id = models.IntegerField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "psm_stock_transfer"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(source_location=F("destination_location")),
                name="psm_transfer_distinct_locs",
            ),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="psm_transfer_qty_positive"),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_transfer_status_idx"),
        ]
