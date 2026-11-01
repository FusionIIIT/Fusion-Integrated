from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class SpecialFoodRequest(TimeStampedModel, UserScopedModel):
    REQUESTED_CHOICES = [
        ("REQUESTED", "Requested"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    ILLNESS_PERSONAL_EVENT_CHOICES = [
        ("FAMILY_MEDICAL_EVENT", "Family Medical Event"),
        ("WORK_MEDICAL_EVENT", "Work Medical Event"),
        ("OTHER_MEDICAL_EVENT", "Other Medical Event"),
        ("PERSONAL_EVENT", "Personal Event"),
    ]

    requested_for = models.DateField()
    reason_type = models.CharField(max_length=20, choices=ILLNESS_PERSONAL_EVENT_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=REQUESTED_CHOICES, default="REQUESTED")
    rejected_by_default = models.BooleanField(default=False)
    charge_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mess_special_food_request"
        indexes = [
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['status', 'created_at'])
        ]

    def __str__(self):
        return f"SpecialFoodRequest {self.id}"
