# Purchase orders, goods receipt notes, and discrepancy/return/warranty cases (CFR-PSM-008..012).
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.psm.domain import state_machine as sm


class PurchaseOrder(TimeStampedModel):
    STATUS = [
        ("issued", "Issued"),
        ("in_transit", "In Transit"),
        ("partially_delivered", "Partially Delivered"),
        ("delivered", "Delivered"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    po_number = models.CharField(max_length=32, unique=True)
    indent = models.ForeignKey("Indent", on_delete=models.PROTECT, related_name="purchase_orders")
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="purchase_orders")
    tender = models.ForeignKey(
        "Tender", on_delete=models.PROTECT, null=True, blank=True, related_name="purchase_orders"
    )
    ordered_quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=24, choices=STATUS, default="issued")
    planned_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)
    issued_by_user_id = models.IntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_purchase_order"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ordered_quantity__gt=0) & Q(unit_price__gt=0) & Q(total_amount__gt=0),
                name="psm_po_amounts_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_po_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.po_number} ({self.status})"


class GoodsReceiptNote(TimeStampedModel):
    STATUS = [
        ("accepted", "Accepted"),
        ("partial", "Partial"),
        ("rejected", "Rejected"),
        ("confirmed", "Confirmed"),
    ]

    grn_number = models.CharField(max_length=32, unique=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, null=True, blank=True, related_name="grns"
    )
    internal_issue = models.ForeignKey(
        "InternalIssue", on_delete=models.PROTECT, null=True, blank=True, related_name="grns"
    )
    replacement_for_case = models.ForeignKey(
        "DiscrepancyCase",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="replacement_grns",
    )
    inspected_by_user_id = models.IntegerField()
    received_quantity = models.PositiveIntegerField()
    accepted_quantity = models.PositiveIntegerField()
    rejected_quantity = models.PositiveIntegerField(default=0)
    inspection_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS)
    confirmed_by_user_id = models.IntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    stock_posted = models.BooleanField(default=False)
    stock_posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_grn"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(purchase_order__isnull=False, internal_issue__isnull=True)
                    | Q(purchase_order__isnull=True, internal_issue__isnull=False)
                ),
                name="psm_grn_single_source",
            ),
            models.CheckConstraint(
                condition=Q(received_quantity__gt=0), name="psm_grn_received_positive"
            ),
            models.CheckConstraint(
                condition=Q(received_quantity=F("accepted_quantity") + F("rejected_quantity")),
                name="psm_grn_qty_balance",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_grn_status_idx"),
        ]


class DiscrepancyCase(TimeStampedModel):
    TYPES = [
        ("damage", "Damage"),
        ("shortage", "Shortage"),
        ("wrong_item", "Wrong Item"),
        ("quality_defect", "Quality Defect"),
    ]
    RESOLUTIONS = [
        ("return", "Return"),
        ("replacement", "Replacement"),
        ("warranty", "Warranty"),
        ("adjustment", "Adjustment"),
    ]
    STATUS = [(s, s.replace("_", " ").title()) for s in sm.DISCREPANCY_STATES]

    case_number = models.CharField(max_length=32, unique=True)
    grn = models.ForeignKey(
        GoodsReceiptNote, on_delete=models.PROTECT, related_name="discrepancy_cases"
    )
    reported_by_user_id = models.IntegerField()
    discrepancy_type = models.CharField(max_length=24, choices=TYPES)
    affected_quantity = models.PositiveIntegerField()
    description = models.TextField()
    evidence_url = models.URLField(max_length=500, blank=True)
    evidence_filename = models.CharField(max_length=120, blank=True)
    requested_resolution = models.CharField(max_length=24, choices=RESOLUTIONS)
    status = models.CharField(max_length=24, choices=STATUS, default=sm.DISC_OPEN)
    replacement_count = models.PositiveSmallIntegerField(default=0)
    resolution_notes = models.TextField(blank=True)
    inventory_adjusted = models.BooleanField(default=False)
    accounting_adjusted = models.BooleanField(default=False)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_discrepancy_case"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(affected_quantity__gt=0) & Q(replacement_count__lte=1),
                name="psm_discrepancy_bounds",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_discrepancy_status_idx"),
        ]


class DiscrepancyCommunication(models.Model):
    """Append-only vendor communication log for discrepancy/warranty cases (AFR-PSM-052)."""

    case = models.ForeignKey(
        DiscrepancyCase, on_delete=models.CASCADE, related_name="communications"
    )
    sender_label = models.CharField(max_length=120)
    message = models.TextField()
    recorded_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_discrepancy_comm"
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"comm#{self.pk} case#{self.case_id}"
