from django.db import models
from decimal import Decimal

class Complaint(models.Model):
    CATEGORY_CHOICES = [
        ("CIVIL", "Civil Infrastructure"),
        ("ELECTRICAL", "Electrical Infrastructure"),
    ]
    URGENCY_CHOICES = [
        ("NORMAL", "Normal Priority"),
        ("URGENT", "Urgent Priority"),
    ]
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("ASSIGNED", "Assigned to Engineer"),
        ("ASSESSED", "Assessed & Estimated"),
        ("ESTIMATE_APPROVED", "Estimate Approved"),
        ("IN_PROGRESS", "Execution in Progress"),
        ("COMPLETED", "Work Completed"),
        ("VERIFIED", "Physically Verified"),
        ("RESOLVED", "Resolved"),
        ("REJECTED", "Rejected"),
        ("CLOSED", "Closed"),
    ]

    requester_id = models.CharField(max_length=64, db_index=True)
    department = models.CharField(max_length=128)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    urgency = models.CharField(max_length=32, choices=URGENCY_CHOICES, default="NORMAL")
    remarks = models.TextField(blank=True, default="")
    assigned_engineer_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="SUBMITTED", db_index=True)
    fast_tracked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Complaint #{self.id} - {self.title} ({self.status})"


class Estimate(models.Model):
    BAND_CHOICES = [
        ("LOW", "Below Rs. 25,000"),
        ("MID", "Rs. 25,000 to Rs. 2.5 Lakh"),
        ("HIGH", "Above Rs. 2.5 Lakh"),
    ]
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PENDING_COMMITTEE", "Pending Committee Review"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("FORWARDED_TO_DIRECTOR", "Forwarded to Director"),
    ]

    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="estimate")
    engineer_id = models.CharField(max_length=64)
    time_days = models.PositiveIntegerField(help_text="Estimated completion time in days")
    material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cost_band = models.CharField(max_length=16, choices=BAND_CHOICES, default="LOW")
    committee_reviewed = models.BooleanField(default=False)
    committee_remarks = models.TextField(blank=True, default="")
    forwarded_to_director = models.BooleanField(default=False)
    director_sanction_reference = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="DRAFT")
    rejection_reason = models.TextField(blank=True, default="")
    approved_by_id = models.CharField(max_length=64, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.total_cost = self.material_cost + self.labor_cost + self.other_cost
        if self.total_cost < Decimal("25000.00"):
            self.cost_band = "LOW"
        elif self.total_cost <= Decimal("250000.00"):
            self.cost_band = "MID"
        else:
            self.cost_band = "HIGH"
        super().save(*args, **kwargs)


class InventoryItem(models.Model):
    item_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=Complaint.CATEGORY_CHOICES)
    unit = models.CharField(max_length=32)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    min_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("10.00"))

    def __str__(self):
        return f"{self.item_code} - {self.name} ({self.current_stock} {self.unit})"


class InventoryMovement(models.Model):
    MOVEMENT_CHOICES = [
        ("ISSUE", "Material Issue to Work"),
        ("RESTOCK", "Restocked via Procurement"),
        ("RETURN", "Returned to Store"),
    ]
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
    complaint = models.ForeignKey(Complaint, on_delete=models.SET_NULL, null=True, blank=True, related_name="material_issues")
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    performed_by_id = models.CharField(max_length=64)
    audit_note = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class ProcurementRequest(models.Model):
    TYPE_CHOICES = [
        ("INTERNAL_QUOTATION", "Low-Cost Internal Quotation"),
        ("COMPETITIVE_BIDDING", "High-Cost Competitive Bidding"),
    ]
    STATUS_CHOICES = [
        ("REQUESTED", "Requested by Admin"),
        ("APPROVED", "Procurement Approved"),
        ("IN_BIDDING", "Bidding in Progress"),
        ("VENDOR_SELECTED", "Vendor Selected"),
        ("COMPLETED", "Stock Received"),
        ("REJECTED", "Procurement Rejected"),
    ]

    complaint = models.ForeignKey(Complaint, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(InventoryItem, on_delete=models.SET_NULL, null=True, blank=True)
    item_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    procurement_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="REQUESTED")
    selected_vendor = models.CharField(max_length=255, blank=True, default="")
    vendor_selection_approved_by = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class PhysicalVerification(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="verifications")
    verified_by_id = models.CharField(max_length=64)  # Department Head / Designated Engineer
    passed = models.BooleanField()
    remarks = models.TextField()
    rework_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class FinalBill(models.Model):
    SETTLEMENT_CHOICES = [
        ("SUBMITTED", "Submitted by Engineer"),
        ("AUDITOR_VERIFIED", "Auditor Verified"),
        ("DIRECTOR_APPROVED", "Director Approved"),
        ("SETTLED_BY_ACCOUNTS", "Settled by Accounts"),
        ("REJECTED", "Audit Rejected"),
    ]

    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="final_bill")
    bill_number = models.CharField(max_length=64, unique=True)
    submitted_by_id = models.CharField(max_length=64)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    auditor_id = models.CharField(max_length=64, blank=True, default="")
    auditor_verified = models.BooleanField(default=False)
    auditor_remarks = models.TextField(blank=True, default="")
    director_approved = models.BooleanField(default=False)
    director_remarks = models.TextField(blank=True, default="")
    settlement_status = models.CharField(max_length=32, choices=SETTLEMENT_CHOICES, default="SUBMITTED")
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Feedback(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField(help_text="Rating between 1 and 5")
    comments = models.TextField(blank=True, default="")
    post_repair_issue = models.BooleanField(default=False)
    issue_description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class ApprovalAuditLog(models.Model):
    entity_type = models.CharField(max_length=32)
    entity_id = models.CharField(max_length=64)
    action = models.CharField(max_length=64)
    actor_id = models.CharField(max_length=64)
    actor_role = models.CharField(max_length=64)
    remarks = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
