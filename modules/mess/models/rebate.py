from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class RebateRequest(TimeStampedModel, UserScopedModel):
    REASON_CHOICES = [
        ("medical", "Medical"),
        ("institute_leave", "Institute Leave"),
        ("family_function", "Family Function"),
        ("other", "Other"),
    ]

    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    explanation = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    approved_start_date = models.DateField(blank=True, null=True)
    approved_end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=(
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ), default="PENDING")
    decided_by_user_id = models.IntegerField(blank=True, null=True)
    decided_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "rebate_request"
        constraints = [
            models.CheckConstraint(check=~Q(end_date__lt=F('start_date')), name="end_date_greater_than_start_date"),
            models.Index(name="rebate_request_user_id_status", fields=['user_id', 'status'])
        ]

    def __str__(self):
        return f"RebateRequest: {self.id}"
