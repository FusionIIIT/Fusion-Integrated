from django.db import models

from modules.iwd.models.complaint import Complaint


class PhysicalVerification(models.Model):
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

    def __str__(self):
        return f"Verification for {self.complaint_id} (Approved: {self.is_approved})"


class FinalBill(models.Model):
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

    def __str__(self):
        return f"FinalBill {self.invoice_number} ({self.settlement_status})"


class ComplaintFeedback(models.Model):
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
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="iwd_valid_feedback_rating_1_to_5",
            ),
        ]

    def __str__(self):
        return f"Feedback {self.rating}/5 for {self.complaint_id}"
