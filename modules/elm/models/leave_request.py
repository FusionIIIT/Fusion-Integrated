from django.db import models


class LeaveRequest(models.Model):
    LEAVE_CHOICES = (
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    )

    DAY_PART_CHOICES = (
        ("FULL", "Full day"),
        ("FIRST_HALF", "First half"),
        ("SECOND_HALF", "Second half"),
    )

    STATUS_CHOICES = (
        ("SUBMITTED", "Submitted"),
        ("PENDING_UNIT_HEAD", "Pending Unit Head"),
        ("PENDING_SANCTION", "Pending sanction"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
    )

    # Fusion identities are managed externally; store the IAM user ID.
    user_id = models.IntegerField(db_index=True)

    leave_type_code = models.CharField(max_length=3, choices=LEAVE_CHOICES)
    requested_start_date = models.DateField()
    requested_end_date = models.DateField()
    day_part = models.CharField(
        max_length=12,
        choices=DAY_PART_CHOICES,
        default="FULL",
    )
    total_days = models.DecimalField(max_digits=6, decimal_places=2)

    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default="SUBMITTED",
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"

    def __str__(self):
        return (
            f"User {self.user_id}: {self.leave_type_code} leave "
            f"from {self.requested_start_date} to {self.requested_end_date} "
            f"({self.status})"
        )
