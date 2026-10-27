"""Leave tables. People are plain user_id ints, no user table here."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORY = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]
    STATUS = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting Substitute"),
        ("unit_head_queue", "Unit Head Queue"),
        ("establishment", "Establishment"),
        ("final_decision", "Final Decision"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    HALF_DAY_PERIOD = [
        ("none", "Full Day"),
        ("FN", "Forenoon"),
        ("AN", "Afternoon"),
    ]
    SUBSTITUTE_STATUS = [
        ("none", "Not Required"),
        ("pending", "Pending Consent"),
        ("accepted", "Consent Accepted"),
        ("declined", "Consent Declined"),
    ]

    category = models.CharField(max_length=8, choices=CATEGORY)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=8, choices=HALF_DAY_PERIOD, default="none")
    days_count = models.FloatField(default=1.0)
    purpose = models.TextField(blank=True)
    station_leave = models.BooleanField(default=False)
    station_details = models.CharField(max_length=300, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, choices=SUBSTITUTE_STATUS, default="none")
    substitute_remarks = models.CharField(max_length=300, blank=True)
    unit_head_remarks = models.TextField(blank=True)
    authority_remarks = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="draft")

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_user_idx"),
            models.Index(fields=["status"], name="leave_status_idx"),
            models.Index(fields=["substitute_user_id", "substitute_status"], name="leave_sub_idx"),
        ]

    def __str__(self):
        return f"leave#{self.pk} u{self.user_id} {self.category} {self.status}"


class LeaveTransition(models.Model):
    """Append-only audit of status change."""
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_transition"
        indexes = [models.Index(fields=["request", "at"], name="leave_tr_idx")]


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Annual entitlement tracking per user and category (BR-EL-001..009)."""
    year = models.IntegerField()
    category = models.CharField(max_length=8, choices=LeaveRequest.CATEGORY)
    allocated = models.FloatField(default=0.0)
    used = models.FloatField(default=0.0)
    pending = models.FloatField(default=0.0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "category"], name="uniq_usr_yr_cat")
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_bal_user_yr_idx"),
        ]

    @property
    def available(self) -> float:
        return max(0.0, self.allocated - self.used - self.pending)

    def __str__(self):
        return f"bal u{self.user_id} {self.year} {self.category}: {self.available}/{self.allocated}"
