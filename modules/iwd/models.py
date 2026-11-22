"""Database models and persistence schema for the Institute Work Department (IWD) module."""

from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel


class ComplaintCategory(models.TextChoices):
    """Recognised categories for maintenance complaints."""

    CIVIL = "Civil", "Civil"
    ELECTRICAL = "Electrical", "Electrical"


class ComplaintUrgency(models.TextChoices):
    """Urgency classification levels for maintenance complaints."""

    LOW = "Low", "Low"
    MEDIUM = "Medium", "Medium"
    HIGH = "High", "High"
    URGENT = "Urgent", "Urgent"


class CostBand(models.TextChoices):
    """Cost band tiers for estimate approval routing."""

    LOW = "LOW", "Low (< Rs.25,000)"
    MID = "MID", "Mid (Rs.25,000 - Rs.2.5 Lakh)"
    HIGH = "HIGH", "High (> Rs.2.5 Lakh)"


class Complaint(TimeStampedModel):
    """A maintenance complaint record submitted by an institute employee."""

    requester_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=50, choices=ComplaintCategory.choices)
    location = models.CharField(max_length=255)
    urgency = models.CharField(
        max_length=20, choices=ComplaintUrgency.choices, default=ComplaintUrgency.LOW
    )
    remarks = models.TextField(blank=True, default="")

    assigned_engineer_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=50, default="Submitted", db_index=True)

    assessment_details = models.TextField(blank=True, default="")
    assessment_date = models.DateTimeField(null=True, blank=True)

    is_urgent_escalated = models.BooleanField(default=False)
    urgent_remarks = models.TextField(blank=True, default="")

    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    rework_count = models.IntegerField(default=0)

    class Meta:
        """Model constraints and table metadata."""

        db_table = "iwd_complaint"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(rework_count__lte=1),
                name="iwd_complaint_max_one_rework",
            ),
        ]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Complaint #{self.pk} ({self.status})"


class Estimate(TimeStampedModel):
    """A repair time, material, and cost estimate submitted by an assigned engineer."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="estimates")
    engineer_user_id = models.IntegerField(db_index=True)
    estimated_time_days = models.IntegerField(default=1)
    materials_details = models.TextField(blank=True, default="")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cost_band = models.CharField(max_length=20, choices=CostBand.choices)

    committee_outcome = models.TextField(blank=True, default="")
    committee_approved = models.BooleanField(null=True, blank=True)

    dept_head_decision = models.CharField(max_length=50, blank=True, default="")
    dept_head_remarks = models.TextField(blank=True, default="")

    director_decision = models.CharField(max_length=50, blank=True, default="")
    director_remarks = models.TextField(blank=True, default="")

    rejection_reason = models.TextField(blank=True, default="")
    resubmission_count = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="Pending")

    class Meta:
        """Model constraints and table metadata."""

        db_table = "iwd_estimate"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(total_cost__gte=Decimal("0.00")),
                name="iwd_estimate_cost_non_negative",
            ),
        ]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Estimate #{self.pk} for Complaint #{self.complaint_id}"


class InventoryItem(models.Model):
    """An inventory stock item maintained by the IWD admin."""

    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=50, default="General")
    stock_quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=50, default="pcs")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        """Model constraints and table metadata."""

        db_table = "iwd_inventory_item"
        constraints = [
            CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="iwd_stock_quantity_non_negative",
            ),
        ]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"{self.name} ({self.stock_quantity} {self.unit})"


class MaterialIssue(models.Model):
    """An audit record of materials issued from inventory against an approved complaint."""

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="material_issues"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    issued_by_user_id = models.IntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        """Model constraints and table metadata."""

        db_table = "iwd_material_issue"
        constraints = [
            CheckConstraint(
                condition=Q(quantity__gt=0),
                name="iwd_material_issue_quantity_positive",
            ),
        ]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Issue #{self.pk} - {self.quantity} of {self.item.name}"


class VerificationRecord(models.Model):
    """A physical quality verification record recorded by the Department Head."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="verifications")
    verifier_user_id = models.IntegerField()
    outcome = models.CharField(max_length=50)
    remarks = models.TextField(blank=True, default="")
    verified_at = models.DateTimeField(auto_now_add=True)
    traversal_number = models.IntegerField(default=0)

    class Meta:
        """Model metadata."""

        db_table = "iwd_verification_record"
        ordering = ["-verified_at"]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Verification #{self.pk}: {self.outcome}"


class FinalBill(TimeStampedModel):
    """A final bill submitted by an engineer following physical verification approval."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="final_bills")
    engineer_user_id = models.IntegerField(db_index=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    auditor_status = models.CharField(max_length=50, default="Pending")
    auditor_remarks = models.TextField(blank=True, default="")
    audited_at = models.DateTimeField(null=True, blank=True)

    director_approved = models.BooleanField(default=False)
    director_approved_at = models.DateTimeField(null=True, blank=True)

    settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)
    settlement_reference = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        """Model metadata."""

        db_table = "iwd_final_bill"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"FinalBill #{self.pk} (Rs.{self.total_amount})"


class ComplaintFeedback(models.Model):
    """User feedback, rating, and post-repair incident reporting on a resolved complaint."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="feedbacks")
    employee_user_id = models.IntegerField(db_index=True)
    rating = models.IntegerField()
    comments = models.TextField(blank=True, default="")
    post_repair_issue = models.BooleanField(default=False)
    post_repair_remarks = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Model constraints and table metadata."""

        db_table = "iwd_complaint_feedback"
        constraints = [
            CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="iwd_feedback_rating_range_1_to_5",
            ),
        ]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Feedback #{self.pk} (Rating {self.rating}/5)"


class DecisionAuditTrail(models.Model):
    """An immutable audit trail entry for approvals, rejections, and state modifications."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="audit_trails")
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=50)
    action = models.CharField(max_length=100)
    previous_state = models.CharField(max_length=50)
    new_state = models.CharField(max_length=50)
    remarks = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Model metadata."""

        db_table = "iwd_decision_audit_trail"
        ordering = ["timestamp"]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"Audit #{self.pk}: {self.actor_role} - {self.action}"
