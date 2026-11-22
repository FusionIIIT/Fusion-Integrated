from decimal import Decimal

from django.db import models

from modules.iwd.models.complaint import Complaint


class RepairEstimate(models.Model):
    COST_BAND_CHOICES = [
        ("low", "Low-Cost (< Rs. 25,000)"),
        ("mid", "Mid-Range (Rs. 25,000 to Rs. 2.5 Lakh)"),
        ("high", "High-Cost (> Rs. 2.5 Lakh)"),
    ]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="estimates"
    )
    version = models.IntegerField(default=1)
    engineer_id = models.IntegerField()
    time_estimate_days = models.IntegerField()
    materials_cost = models.DecimalField(max_digits=12, decimal_places=2)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2)
    other_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    cost_band = models.CharField(max_length=20, choices=COST_BAND_CHOICES)
    status = models.CharField(max_length=50, default="pending_review")
    rejection_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iwd_repair_estimate"
        constraints = [
            models.UniqueConstraint(
                fields=["complaint", "version"],
                name="iwd_unique_complaint_estimate_version",
            ),
            models.CheckConstraint(
                condition=models.Q(total_cost__gte=0),
                name="iwd_non_negative_estimate_total",
            ),
            models.CheckConstraint(
                condition=models.Q(time_estimate_days__gt=0),
                name="iwd_positive_estimate_days",
            ),
        ]

    def __str__(self):
        return f"Estimate v{self.version} for {self.complaint_id}"


class ReviewCommitteeOutcome(models.Model):
    estimate = models.OneToOneField(
        RepairEstimate, on_delete=models.CASCADE, related_name="committee_review"
    )
    reviewer_user_id = models.IntegerField()
    is_feasible = models.BooleanField(default=True)
    is_necessary = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_committee_outcome"

    def __str__(self):
        return f"Committee review for estimate {self.estimate_id}"
