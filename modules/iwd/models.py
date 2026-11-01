"""Domain models for Institute Work Department (IWD)."""
from decimal import Decimal
from django.db import models


class ComplaintCategory(models.TextChoices):
    CIVIL = "CIVIL", "Civil"
    ELECTRICAL = "ELECTRICAL", "Electrical"
    CARPENTRY = "CARPENTRY", "Carpentry"
    PLUMBING = "PLUMBING", "Plumbing"
    SANITARY = "SANITARY", "Sanitary"
    OTHER = "OTHER", "Other"


class ComplaintStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    ASSIGNED = "ASSIGNED", "Assigned"
    ASSESSED = "ASSESSED", "Assessed"
    ESTIMATE_PENDING = "ESTIMATE_PENDING", "Estimate Pending"
    ESTIMATE_APPROVED = "ESTIMATE_APPROVED", "Estimate Approved"
    MATERIALS_AVAILABLE = "MATERIALS_AVAILABLE", "Materials Available"
    MATERIALS_ISSUED = "MATERIALS_ISSUED", "Materials Issued"
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION", "Ready for Execution"
    VERIFICATION_PENDING = "VERIFICATION_PENDING", "Verification Pending"
    REWORK_REQUIRED = "REWORK_REQUIRED", "Rework Required"
    RESOLVED = "RESOLVED", "Resolved"
    BILL_SUBMITTED = "BILL_SUBMITTED", "Bill Submitted"
    AUDIT_PENDING = "AUDIT_PENDING", "Audit Pending"
    DIRECTOR_PAYMENT_PENDING = "DIRECTOR_PAYMENT_PENDING", "Director Payment Pending"
    SETTLED = "SETTLED", "Settled"
    REJECTED = "REJECTED", "Rejected"


class EstimateStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    LOW_COST_PENDING = "LOW_COST_PENDING", "Low-Cost Review Pending"
    MID_RANGE_COMMITTEE_PENDING = "MID_RANGE_COMMITTEE_PENDING", "Mid-Range Committee Review Pending"
    DEPT_HEAD_PENDING = "DEPT_HEAD_PENDING", "Department Head Review Pending"
    DIRECTOR_PENDING = "DIRECTOR_PENDING", "Director Review Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED_LOW = "REJECTED_LOW", "Rejected - Low-Cost"
    REJECTED_MID = "REJECTED_MID", "Rejected - Mid-Range"
    REJECTED_DIRECTOR = "REJECTED_DIRECTOR", "Rejected - Director Route"


class Complaint(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=32, choices=ComplaintCategory.choices, default=ComplaintCategory.CIVIL)
    location = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, default="")
    complainant_user_id = models.CharField(max_length=128)
    assigned_engineer_id = models.CharField(max_length=128, blank=True, default="")
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=64, choices=ComplaintStatus.choices, default=ComplaintStatus.SUBMITTED)
    assessment_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iwd_complaints"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Complaint #{self.pk} - {self.title} ({self.status})"


class Estimate(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="estimates")
    engineer_id = models.CharField(max_length=128)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cost_band = models.CharField(max_length=16, default="LOW")
    status = models.CharField(max_length=64, choices=EstimateStatus.choices, default=EstimateStatus.DRAFT)
    committee_remarks = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    approved_by = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iwd_estimates"

    def __str__(self):
        return f"Estimate #{self.pk} for Complaint #{self.complaint_id} (Rs. {self.total_cost})"


class InventoryItem(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    unit = models.CharField(max_length=32, default="units")
    quantity_in_stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)

    class Meta:
        db_table = "iwd_inventory_items"

    def __str__(self):
        return f"{self.name} ({self.quantity_in_stock} {self.unit})"


class InventoryMovement(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
    complaint = models.ForeignKey(Complaint, on_delete=models.SET_NULL, null=True, blank=True)
    movement_type = models.CharField(max_length=32, choices=[("ISSUE", "Issue"), ("RECEIVE", "Receive"), ("RETURN", "Return")])
    quantity = models.IntegerField()
    recorded_by = models.CharField(max_length=128)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_inventory_movements"


class ProcurementRequest(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="procurements")
    item_description = models.TextField()
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    procurement_mode = models.CharField(max_length=32, choices=[("INTERNAL_QUOTE", "Internal Quotation"), ("BIDDING", "External Bidding")])
    selected_vendor = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=32, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_procurement_requests"


class WorkVerification(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="verifications")
    verified_by = models.CharField(max_length=128)
    passed = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, default="")
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_work_verifications"


class BillAndSettlement(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="bills")
    submitted_by = models.CharField(max_length=128)
    billed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    auditor_id = models.CharField(max_length=128, blank=True, default="")
    auditor_validated = models.BooleanField(default=False)
    auditor_notes = models.TextField(blank=True, default="")
    director_approved = models.BooleanField(default=False)
    settlement_status = models.CharField(max_length=32, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iwd_bills_settlement"


class ComplaintFeedback(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    user_id = models.CharField(max_length=128)
    rating = models.PositiveSmallIntegerField()  # 1 to 5
    comments = models.TextField(blank=True, default="")
    has_post_repair_issue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_complaint_feedback"

