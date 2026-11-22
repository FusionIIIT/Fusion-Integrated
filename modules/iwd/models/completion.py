from django.db import models
from django.db.models import Q

from modules.iwd.models.complaint import Complaint


class PhysicalVerification(models.Model):
    """Department Head physical verification of completed work."""

    complaint = models.OneToOneField(
        Complaint, on_delete=models.CASCADE, related_name="physical_verification"
    )
    verified_by_user_id = models.IntegerField()
    is_approved = models.BooleanField()
    verification_remarks = models.TextField(blank=True, default="")
    rework_notes = models.TextField(blank=True, default="")
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_physical_verification"


class FinalBill(models.Model):
    """Final bill submitted by engineer."""

    complaint = models.OneToOneField(
        Complaint, on_delete=models.CASCADE, related_name="final_bill"
    )
    engineer_id = models.IntegerField()
    invoice_number = models.CharField(max_length=100)
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_audited = models.BooleanField(default=False)
    auditor_user_id = models.IntegerField(null=True, blank=True)
    audit_remarks = models.TextField(blank=True, default="")
    audit_timestamp = models.DateTimeField(null=True, blank=True)

    director_approved = models.BooleanField(default=False)
    director_user_id = models.IntegerField(null=True, blank=True)
    director_approved_at = models.DateTimeField(null=True, blank=True)

    settlement_status = models.CharField(max_length=30, default="pending")
    accounts_reference = models.CharField(max_length=100, blank=True, default="")
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iwd_final_bill"


class ComplaintFeedback(models.Model):
    """Feedback and rating from employee after resolution."""

    complaint = models.OneToOneField(
        Complaint, on_delete=models.CASCADE, related_name="feedback"
    )
    user_id = models.IntegerField()
    rating = models.IntegerField()
    feedback_text = models.TextField(blank=True, default="")
    post_repair_issue = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_complaint_feedback"
        constraints = [
            models.CheckConstraint(
                check=Q(rating__gte=1) & Q(rating__lte=5),
                name="iwd_valid_feedback_rating_1_to_5",
            ),
        ]
