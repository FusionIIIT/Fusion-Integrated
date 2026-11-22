from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from core.db.mixins import TimeStampedModel


class Vendor(TimeStampedModel):
    name = models.CharField(max_length=255)
    gst_number = models.CharField(max_length=15, unique=True)
    bank_account_number = models.CharField(max_length=50)
    bank_ifsc = models.CharField(max_length=20)
    compliance_docs_url = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name


class StockItem(TimeStampedModel):
    item_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    department = models.CharField(max_length=100)
    central_stock = models.PositiveIntegerField(default=0)
    department_stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.item_code


class Indent(TimeStampedModel):
    indent_id = models.CharField(max_length=64, unique=True)
    # Plain integer ID instead of cross-module ForeignKey (CI Rule Enforced)
    requestor_id = models.IntegerField()
    item_details = models.TextField()
    quantity = models.PositiveIntegerField()
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    justification = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=[
            ('DRAFT', 'Draft'),
            ('SUBMITTED', 'Submitted'),
            ('STOCK_CHECKED', 'Stock Checked'),
            ('DEPT_REVIEWED', 'Department Reviewed'),
            ('HEAD_RECOMMENDED', 'Head Recommended'),
            ('AWAITING_FINAL_APPROVAL', 'Awaiting Final Approval'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('WITHDRAWN', 'Withdrawn'),
        ],
        default='SUBMITTED',
    )
    priority = models.CharField(
        max_length=16,
        choices=[('NORMAL', 'Normal'), ('HIGH', 'High'), ('CRITICAL', 'Critical')],
        default='NORMAL',
    )
    is_duplicate = models.BooleanField(default=False)
    rejection_justification = models.TextField(blank=True, null=True)
    current_version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.indent_id


class IndentVersion(TimeStampedModel):
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    item_details = models.TextField()
    quantity = models.PositiveIntegerField()
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    justification = models.TextField()

    def __str__(self):
        return f"{self.indent.indent_id} - Version {self.version_number}"


class PurchaseOrder(TimeStampedModel):
    po_number = models.CharField(max_length=64, unique=True)
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    procurement_method = models.CharField(
        max_length=16,
        choices=[('DIRECT', 'Direct'), ('TENDER', 'Tender')],
        default='DIRECT',
    )
    status = models.CharField(
        max_length=32,
        choices=[
            ('ISSUED', 'Issued'),
            ('DELIVERED', 'Delivered'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='ISSUED',
    )
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_schedule = models.DateField()

    def __str__(self):
        return self.po_number


class GoodsReceiptNote(TimeStampedModel):
    grn_number = models.CharField(max_length=64, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    accepted_quantity = models.PositiveIntegerField()
    rejected_quantity = models.PositiveIntegerField(default=0)
    inspection_remarks = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)
    has_discrepancy = models.BooleanField(default=False)

    def __str__(self):
        return self.grn_number


class StockTransfer(TimeStampedModel):
    transfer_id = models.CharField(max_length=64, unique=True)
    source_department = models.CharField(max_length=100)
    destination_department = models.CharField(max_length=100)
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=32,
        choices=[
            ('REQUESTED', 'Requested'),
            ('DISPATCHED', 'Dispatched'),
            ('COMPLETED', 'Completed'),
        ],
        default='REQUESTED',
    )

    def __str__(self):
        return self.transfer_id