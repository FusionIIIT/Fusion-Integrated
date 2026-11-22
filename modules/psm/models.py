"""Data models for Purchase and Stores Management (PSM)."""
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class Indent(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved_internal", "Approved (Internal Issue)"),
        ("approved_external", "Approved (External Procurement)"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    CRITICALITY_CHOICES = [
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    indent_number = models.CharField(max_length=64, unique=True, db_index=True)
    department_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    justification = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", db_index=True)
    criticality = models.CharField(max_length=16, choices=CRITICALITY_CHOICES, default="normal")
    total_estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_duplicate_flag = models.BooleanField(default=False)
    duplicate_notes = models.CharField(max_length=255, blank=True)
    rejection_reason = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_indents"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.indent_number} - {self.title}"

class IndentItem(TimeStampedModel):
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "psm_indent_items"

class IndentApproval(TimeStampedModel):
    ACTION_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("recommended", "Recommended"),
        ("rejected", "Rejected"),
        ("changes_requested", "Changes Requested"),
    ]

    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="approvals")
    approver_user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=64)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default="pending")
    remarks = models.TextField(blank=True)
    action_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_indent_approvals"
        ordering = ["created_at"]

class StockItem(TimeStampedModel):
    item_code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=32, default="units")
    department_id = models.IntegerField(null=True, blank=True, db_index=True)
    is_central = models.BooleanField(default=False)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reserved_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "psm_stock_items"

    @property
    def available_quantity(self):
        return max(self.current_quantity - self.reserved_quantity, 0)

class StockReservation(TimeStampedModel):
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="reservations")
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, null=True, blank=True, related_name="reservations")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=24, default="active", db_index=True)

    class Meta:
        db_table = "psm_stock_reservations"

class StockTransfer(TimeStampedModel):
    transfer_number = models.CharField(max_length=64, unique=True, db_index=True)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="transfers")
    from_department_id = models.IntegerField(db_index=True)
    to_department_id = models.IntegerField(db_index=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=24, default="requested", db_index=True)
    requested_by = models.IntegerField(db_index=True)
    dispatched_by = models.IntegerField(null=True, blank=True)
    received_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "psm_stock_transfers"

class Vendor(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, unique=True, db_index=True)
    gst_number = models.CharField(max_length=32)
    pan_number = models.CharField(max_length=32, blank=True)
    bank_name = models.CharField(max_length=128)
    bank_account_number = models.CharField(max_length=64)
    ifsc_code = models.CharField(max_length=32)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=32)
    address = models.TextField()
    is_verified = models.BooleanField(default=False, db_index=True)
    compliance_documents_valid = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)

    class Meta:
        db_table = "psm_vendors"

class PurchaseOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("partially_delivered", "Partially Delivered"),
        ("delivered", "Delivered"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    po_number = models.CharField(max_length=64, unique=True, db_index=True)
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="purchase_orders")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="draft", db_index=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    issue_date = models.DateField(null=True, blank=True)
    delivery_deadline = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "psm_purchase_orders"

class PurchaseOrderItem(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "psm_po_items"

class GoodsReceiptNote(TimeStampedModel):
    grn_number = models.CharField(max_length=64, unique=True, db_index=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, null=True, blank=True, related_name="grns")
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, null=True, blank=True, related_name="grns")
    inspected_by = models.IntegerField(db_index=True)
    receipt_date = models.DateField()
    status = models.CharField(max_length=32, default="accepted", db_index=True)
    inspection_notes = models.TextField(blank=True)
    delivery_confirmed = models.BooleanField(default=False, db_index=True)
    confirmed_by = models.IntegerField(null=True, blank=True)
    stock_posted = models.BooleanField(default=False)

    class Meta:
        db_table = "psm_grns"

class DeliveryDiscrepancy(TimeStampedModel):
    discrepancy_number = models.CharField(max_length=64, unique=True, db_index=True)
    grn = models.ForeignKey(GoodsReceiptNote, on_delete=models.CASCADE, related_name="discrepancies")
    reported_by = models.IntegerField(db_index=True)
    discrepancy_type = models.CharField(max_length=32)
    resolution_type = models.CharField(max_length=32, default="replacement")
    status = models.CharField(max_length=32, default="reported", db_index=True)
    evidence_notes = models.TextField()
    vendor_communication = models.TextField(blank=True)

    class Meta:
        db_table = "psm_discrepancies"

class Invoice(TimeStampedModel):
    invoice_number = models.CharField(max_length=64, unique=True, db_index=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="invoices")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    grn = models.ForeignKey(GoodsReceiptNote, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    invoice_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    match_status = models.CharField(max_length=32, default="pending", db_index=True)
    mismatch_reason = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "psm_invoices"

class Payment(TimeStampedModel):
    payment_reference = models.CharField(max_length=64, unique=True, db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2)
    is_partial = models.BooleanField(default=False)
    status = models.CharField(max_length=24, default="on_hold", db_index=True)
    hold_reason = models.TextField(blank=True)
    processed_by = models.IntegerField(db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_payments"

class PSMAuditLog(models.Model):
    entity_type = models.CharField(max_length=64, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=64)
    actor_user_id = models.IntegerField(db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict)

    class Meta:
        db_table = "psm_audit_logs"
        ordering = ["-timestamp"]
