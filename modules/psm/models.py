import uuid

from django.db import models
from django.db.models import F, Q

from modules.psm.storage import PsmStorage, attachment_path


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self._meta.verbose_name}: {self.pk}"


class Membership(Record):
    user_id = models.BigIntegerField(unique=True)
    role = models.CharField(max_length=32)
    department = models.CharField(max_length=100)
    vendor_id = models.UUIDField(null=True, blank=True)


class Policy(Record):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=False)
    configuration = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["active"], condition=Q(active=True), name="psm_single_active_policy"
            )
        ]


class Vendor(Record):
    name = models.CharField(max_length=160)
    gst = models.CharField(max_length=32)
    bank_details = models.TextField()
    compliance = models.JSONField(default=list)
    verified = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)


class Stock(Record):
    item = models.CharField(max_length=160)
    location = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    reserved = models.DecimalField(max_digits=16, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "location"], name="psm_stock_item_location"),
            models.CheckConstraint(
                condition=Q(quantity__gte=0) & Q(reserved__gte=0) & Q(quantity__gte=F("reserved")),
                name="psm_stock_available",
            ),
        ]


class Indent(Record):
    requestor_id = models.BigIntegerField()
    department = models.CharField(max_length=100)
    item = models.CharField(max_length=160)
    quantity = models.DecimalField(max_digits=16, decimal_places=3)
    estimated_cost = models.DecimalField(max_digits=16, decimal_places=2)
    justification = models.TextField()
    status = models.CharField(max_length=48, default="draft")
    priority = models.IntegerField(default=0)
    duplicate_ids = models.JSONField(default=list)
    duplicate_review = models.TextField(blank=True)
    stock_result = models.JSONField(default=dict)
    method = models.CharField(max_length=16, blank=True)
    approval_route = models.JSONField(default=list)
    approval_step = models.PositiveIntegerField(default=0)
    policy_snapshot = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True)
    dispatch_at = models.DateTimeField(null=True)
    pick_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["department", "status", "-created_at"], name="psm_indent_dept_status"
            ),
            models.Index(fields=["requestor_id", "-created_at"], name="psm_indent_owner"),
        ]


class Reservation(Record):
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="reservations")
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=16, decimal_places=3)
    remaining = models.DecimalField(max_digits=16, decimal_places=3)


class Tender(Record):
    indent = models.OneToOneField(Indent, on_delete=models.PROTECT)
    criteria = models.JSONField(default=list)
    status = models.CharField(max_length=32, default="published")
    closes_at = models.DateTimeField()
    selected_bid_id = models.UUIDField(null=True)
    decision = models.TextField(blank=True)


class Bid(Record):
    tender = models.ForeignKey(Tender, on_delete=models.PROTECT, related_name="bids")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    proposal = models.TextField()
    evaluation = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tender", "vendor"], name="psm_bid_vendor")]


class PurchaseOrder(Record):
    indent = models.OneToOneField(Indent, on_delete=models.PROTECT, related_name="po")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=16, decimal_places=3)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(max_length=32, default="issued")
    planned_delivery = models.DateTimeField()
    actual_delivery = models.DateTimeField(null=True)


class Receipt(Record):
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="receipts")
    accepted = models.DecimalField(max_digits=16, decimal_places=3)
    rejected = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    inspected_by = models.BigIntegerField()
    inspection = models.TextField()
    confirmed_at = models.DateTimeField(null=True)
    posted = models.BooleanField(default=False)
    replacement_case_id = models.UUIDField(null=True)


class Discrepancy(Record):
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, related_name="cases")
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, null=True)
    description = models.TextField()
    evidence = models.JSONField(default=list)
    kind = models.CharField(max_length=24, default="damage")
    status = models.CharField(max_length=32, default="open")
    resolution = models.TextField(blank=True)
    inventory_delta = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    accounting_delta = models.DecimalField(max_digits=16, decimal_places=2, default=0)


class Invoice(Record):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=16, decimal_places=3)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(max_length=24, default="pending")
    hold_reason = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["po", "number"], name="psm_invoice_number")]


class Payment(Record):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)


class Transfer(Record):
    source = models.ForeignKey(Stock, on_delete=models.PROTECT)
    destination = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=16, decimal_places=3)
    status = models.CharField(max_length=32, default="requested")
    requestor_id = models.BigIntegerField()
    reason = models.TextField()


class LedgerEntry(Record):
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT)
    delta = models.DecimalField(max_digits=16, decimal_places=3)
    source = models.CharField(max_length=100)
    reason = models.TextField()
    actor_id = models.BigIntegerField()


class Audit(Record):
    actor_id = models.BigIntegerField()
    department = models.CharField(max_length=100)
    entity = models.CharField(max_length=40)
    object_id = models.UUIDField()
    action = models.CharField(max_length=60)
    snapshot = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["entity", "object_id", "created_at"], name="psm_audit_object")
        ]


class Notification(Record):
    user_id = models.BigIntegerField()
    indent = models.ForeignKey(Indent, on_delete=models.PROTECT, null=True)
    event = models.CharField(max_length=60)
    message = models.TextField()
    read_at = models.DateTimeField(null=True)
    deduplication_key = models.CharField(max_length=160, unique=True)


class Communication(Record):
    case = models.ForeignKey(Discrepancy, on_delete=models.PROTECT, related_name="communications")
    actor_id = models.BigIntegerField()
    message = models.TextField()


class ReportSchedule(Record):
    credential = models.TextField()
    user_id = models.BigIntegerField()
    report = models.CharField(max_length=32)
    filters = models.JSONField(default=dict)
    interval_hours = models.PositiveIntegerField()
    next_run = models.DateTimeField()
    enabled = models.BooleanField(default=True)


class ReportRun(Record):
    user_id = models.BigIntegerField()
    report = models.CharField(max_length=32)
    filters = models.JSONField(default=dict)
    rows = models.JSONField(default=list)
    schedule = models.ForeignKey(ReportSchedule, null=True, on_delete=models.PROTECT)


class VendorVersion(Record):
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    actor_id = models.BigIntegerField()
    snapshot = models.JSONField(default=dict)


class Attachment(Record):
    entity = models.CharField(max_length=16)
    object_id = models.UUIDField()
    actor_id = models.BigIntegerField()
    original_name = models.CharField(max_length=160)
    file = models.FileField(storage=PsmStorage(), upload_to=attachment_path)
