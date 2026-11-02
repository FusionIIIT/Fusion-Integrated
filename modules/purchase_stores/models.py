"""PSM-owned records. Identities and organizational units are external integer references."""

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class Indent(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        STOCK_RESERVED = "STOCK_RESERVED", "Stock reserved"
        EXTERNAL_PROCUREMENT_REQUIRED = (
            "EXTERNAL_PROCUREMENT_REQUIRED",
            "External procurement required",
        )
        DEPARTMENT_REVIEWED = "DEPARTMENT_REVIEWED", "Department reviewed"
        INTERNAL_ISSUE_APPROVED = "INTERNAL_ISSUE_APPROVED", "Internal issue approved"
        DISPATCHED_READY_FOR_RECEIPT = (
            "DISPATCHED_READY_FOR_RECEIPT",
            "Dispatched, ready for receipt",
        )
        DEPARTMENT_HEAD_RECOMMENDED = "DEPARTMENT_HEAD_RECOMMENDED", "Department head recommended"
        AWAITING_FINAL_APPROVAL = "AWAITING_FINAL_APPROVAL", "Awaiting final approval"
        PROCUREMENT_AUTHORIZED = "PROCUREMENT_AUTHORIZED", "Procurement authorized"
        PO_ISSUED = "PO_ISSUED", "Purchase order issued"
        DELIVERED = "DELIVERED", "Delivered"
        GRN_ACCEPTED = "GRN_ACCEPTED", "GRN accepted"
        GRN_PARTIAL = "GRN_PARTIAL", "GRN partially accepted"
        RECEIPT_CONFIRMED = "RECEIPT_CONFIRMED", "Receipt confirmed"
        DISCREPANCY_IDENTIFIED = "DISCREPANCY_IDENTIFIED", "Discrepancy identified"
        DISCREPANCY_CASE_OPEN = "DISCREPANCY_CASE_OPEN", "Discrepancy case open"
        REPLACEMENT_AWAITED = "REPLACEMENT_AWAITED", "Replacement awaited"
        REPLACEMENT_CONFIRMED = "REPLACEMENT_CONFIRMED", "Replacement confirmed"
        INVOICE_VERIFIED = "INVOICE_VERIFIED", "Invoice verified"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
        PAID = "PAID", "Paid"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        CANCELLED = "CANCELLED", "Cancelled"
        REJECTED = "REJECTED", "Rejected"

    reference = models.CharField(max_length=32, unique=True, blank=True)
    requestor_user_id = models.PositiveBigIntegerField(db_index=True)
    department_id = models.PositiveBigIntegerField(db_index=True)
    status = models.CharField(
        max_length=40, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    justification = models.TextField()
    priority = models.CharField(max_length=32, blank=True)
    duplicate_review_required = models.BooleanField(default=False)
    duplicate_of_id = models.PositiveBigIntegerField(null=True, blank=True)
    current_version = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_indent"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["department_id", "status", "-created_at"], name="psm_indent_dept_status_idx"
            ),
            models.Index(fields=["requestor_user_id", "-created_at"], name="psm_indent_owner_idx"),
        ]

    def __str__(self):
        return self.reference or f"Indent {self.pk}"


class IndentLine(TimeStampedModel):
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="lines")
    item_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=40, blank=True)
    estimated_unit_cost = models.DecimalField(max_digits=14, decimal_places=2)
    sku = models.CharField(max_length=80, blank=True, db_index=True)

    class Meta:
        db_table = "psm_indent_line"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="psm_indent_line_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(estimated_unit_cost__gte=0), name="psm_indent_line_cost_nonnegative"
            ),
        ]


class IndentVersion(models.Model):
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    actor_user_id = models.PositiveBigIntegerField()
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_indent_version"
        ordering = ["indent_id", "version"]
        constraints = [
            models.UniqueConstraint(fields=["indent", "version"], name="psm_indent_version_unique")
        ]

    def __str__(self):
        return f"{self.indent.reference} version {self.version}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Indent versions are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Indent versions are append-only.")


class WorkflowAction(models.Model):
    indent = models.ForeignKey(
        Indent, on_delete=models.PROTECT, related_name="actions", null=True, blank=True
    )
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=80, blank=True)
    action = models.CharField(max_length=64)
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40, blank=True)
    reason = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_workflow_action"
        ordering = ["at", "id"]
        indexes = [models.Index(fields=["indent", "at"], name="psm_action_indent_time_idx")]

    def __str__(self):
        return f"{self.action} ({self.indent_id or 'policy'})"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Workflow actions are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Workflow actions are append-only.")


class ApprovalStep(TimeStampedModel):
    class StepStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        SKIPPED = "SKIPPED", "Skipped"

    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="approval_steps")
    sequence = models.PositiveSmallIntegerField()
    role_code = models.CharField(max_length=64)
    assigned_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=StepStatus.choices, default=StepStatus.PENDING)
    decision = models.CharField(max_length=24, blank=True)
    reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_approval_step"
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["indent", "sequence"], name="psm_approval_step_unique")
        ]


class Vendor(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending verification"
        VERIFIED = "VERIFIED", "Verified"
        SUSPENDED = "SUSPENDED", "Suspended"

    legal_name = models.CharField(max_length=200)
    gst_number = models.CharField(max_length=32, blank=True)
    bank_details = models.JSONField(default=dict, blank=True)
    compliance_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    version = models.PositiveIntegerField(default=1)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "psm_vendor"
        ordering = ["legal_name", "id"]


class VendorVersion(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    actor_user_id = models.PositiveBigIntegerField()
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_vendor_version"
        constraints = [
            models.UniqueConstraint(fields=["vendor", "version"], name="psm_vendor_version_unique")
        ]

    def __str__(self):
        return f"{self.vendor.legal_name} version {self.version}"


class StockBalance(TimeStampedModel):
    sku = models.CharField(max_length=80)
    item_name = models.CharField(max_length=200)
    department_id = models.PositiveBigIntegerField(db_index=True)
    quantity_on_hand = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_reserved = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    is_central = models.BooleanField(default=False)

    class Meta:
        db_table = "psm_stock_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["sku", "department_id", "is_central"], name="psm_stock_location_sku_unique"
            ),
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=0), name="psm_stock_on_hand_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(quantity_reserved__gte=0), name="psm_stock_reserved_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(quantity_reserved__lte=F("quantity_on_hand")),
                name="psm_stock_reserved_lte_on_hand",
            ),
        ]

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved


class StockLedgerEntry(models.Model):
    class Kind(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        ISSUE = "ISSUE", "Issue"
        TRANSFER_IN = "TRANSFER_IN", "Transfer in"
        TRANSFER_OUT = "TRANSFER_OUT", "Transfer out"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    stock = models.ForeignKey(StockBalance, on_delete=models.PROTECT, related_name="ledger")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    quantity_delta = models.DecimalField(max_digits=14, decimal_places=3)
    reference = models.CharField(max_length=80, blank=True)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_stock_ledger_entry"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.kind} {self.quantity_delta} {self.stock.sku}"


class StockReservation(TimeStampedModel):
    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        RELEASED = "RELEASED", "Released"
        CONSUMED = "CONSUMED", "Consumed"

    indent_line = models.ForeignKey(
        IndentLine, on_delete=models.PROTECT, related_name="reservations"
    )
    stock = models.ForeignKey(StockBalance, on_delete=models.PROTECT, related_name="reservations")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RESERVED)

    class Meta:
        db_table = "psm_stock_reservation"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="psm_stock_reservation_positive"
            )
        ]


class Tender(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        EVALUATION = "EVALUATION", "Evaluation"
        AWARDED = "AWARDED", "Awarded"
        CANCELLED = "CANCELLED", "Cancelled"

    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="tenders")
    reference = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    evaluation_criteria = models.JSONField(default=list)
    selected_bid = models.ForeignKey(
        "Bid", on_delete=models.SET_NULL, null=True, blank=True, related_name="selected_for"
    )

    class Meta:
        db_table = "psm_tender"


class Bid(TimeStampedModel):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="bids")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="bids")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    proposal = models.JSONField(default=dict, blank=True)
    evaluation = models.JSONField(default=dict, blank=True)
    committee_approved = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_bid"
        constraints = [
            models.UniqueConstraint(fields=["tender", "vendor"], name="psm_bid_vendor_unique")
        ]


class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Issued"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED", "Partially delivered"
        DELIVERED = "DELIVERED", "Delivered"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    reference = models.CharField(max_length=32, unique=True)
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="purchase_orders")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.ISSUED, db_index=True
    )
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    line_items = models.JSONField(default=list)
    planned_delivery_at = models.DateTimeField(null=True, blank=True)
    actual_delivery_at = models.DateTimeField(null=True, blank=True)
    terms = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "psm_purchase_order"
        ordering = ["-created_at", "-id"]


class GoodsReceipt(TimeStampedModel):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="receipts"
    )
    receipt_reference = models.CharField(max_length=32, unique=True)
    inspected_by_user_id = models.PositiveBigIntegerField()
    accepted_lines = models.JSONField(default=list)
    rejected_lines = models.JSONField(default=list)
    discrepancy_note = models.TextField(blank=True)
    receipt_confirmed_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_goods_receipt"


class DiscrepancyCase(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        RETURN = "RETURN", "Return in progress"
        REPLACEMENT = "REPLACEMENT", "Replacement awaited"
        WARRANTY = "WARRANTY", "Warranty in progress"
        RESOLVED = "RESOLVED", "Resolved"

    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.PROTECT, related_name="discrepancies"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    description = models.TextField()
    evidence = models.JSONField(default=list, blank=True)
    resolution = models.TextField(blank=True)
    vendor_communications = models.JSONField(default=list, blank=True)
    replacement_traversal_count = models.PositiveSmallIntegerField(default=0)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_discrepancy_case"
        constraints = [
            models.CheckConstraint(
                condition=Q(replacement_traversal_count__lte=1),
                name="psm_one_replacement_traversal",
            )
        ]


class VendorInvoice(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        ON_HOLD = "ON_HOLD", "On hold"
        VERIFIED = "VERIFIED", "Verified"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
        PAID = "PAID", "Paid"

    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="invoices"
    )
    goods_receipt = models.ForeignKey(
        "GoodsReceipt", on_delete=models.PROTECT, related_name="invoices"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=80)
    invoice_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUBMITTED)
    match_details = models.JSONField(default=dict, blank=True)
    hold_reason = models.TextField(blank=True)
    verified_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_vendor_invoice"
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "invoice_number"], name="psm_invoice_vendor_number_unique"
            )
        ]


class VendorPayment(TimeStampedModel):
    invoice = models.ForeignKey(VendorInvoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=80, blank=True)
    processed_by_user_id = models.PositiveBigIntegerField()
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_vendor_payment"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="psm_payment_amount_positive")
        ]


class StockTransfer(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        DISPATCHED = "DISPATCHED", "Dispatched"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    reference = models.CharField(max_length=32, unique=True)
    source_department_id = models.PositiveBigIntegerField()
    destination_department_id = models.PositiveBigIntegerField()
    requested_by_user_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    lines = models.JSONField(default=list)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_stock_transfer"


class StockTransferReservation(TimeStampedModel):
    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        CONSUMED = "CONSUMED", "Consumed"
        RELEASED = "RELEASED", "Released"

    transfer = models.ForeignKey(
        StockTransfer, on_delete=models.PROTECT, related_name="reservations"
    )
    stock = models.ForeignKey(
        StockBalance, on_delete=models.PROTECT, related_name="transfer_reservations"
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RESERVED)

    class Meta:
        db_table = "psm_stock_transfer_reservation"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="psm_transfer_reservation_positive"
            )
        ]


class PolicySetting(TimeStampedModel):
    """Named policy values; no procurement threshold or SLA is hard-coded in code."""

    key = models.CharField(max_length=80, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "psm_policy_setting"


class DepartmentAccess(TimeStampedModel):
    """PSM scope assignments until IAM publishes numeric department IDs."""

    user_id = models.PositiveBigIntegerField(db_index=True)
    department_id = models.PositiveBigIntegerField(db_index=True)
    assigned_by_user_id = models.PositiveBigIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "psm_department_access"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "department_id"], name="psm_department_access_unique"
            )
        ]


class ScheduledReport(TimeStampedModel):
    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    report_code = models.CharField(max_length=80)
    owner_user_id = models.PositiveBigIntegerField(db_index=True)
    frequency = models.CharField(max_length=8, choices=Frequency.choices)
    output_format = models.CharField(max_length=12, default="csv")
    filters = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    next_run_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "psm_scheduled_report"


class ReportGeneration(models.Model):
    report_code = models.CharField(max_length=80)
    requested_by_user_id = models.PositiveBigIntegerField()
    filters = models.JSONField(default=dict, blank=True)
    output_format = models.CharField(max_length=12, default="json")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_report_generation"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.report_code} by {self.requested_by_user_id}"
