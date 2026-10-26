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
        ("PENDING_SUBSTITUTE", "Pending substitute"),
        ("PENDING_SUBSTITUTE_REPLACEMENT", "Pending substitute replacement"),
        ("PENDING_UNIT_HEAD", "Pending Unit Head"),
        ("PENDING_ESTABLISHMENT", "Pending establishment"),
        ("PENDING_SANCTION", "Pending sanction"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
    )

    # Fusion identities are managed externally; store the IAM user ID.
    user_id = models.IntegerField(db_index=True)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=16,
        choices=(("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined")),
        default="PENDING",
    )
    substitute_replacement_count = models.PositiveSmallIntegerField(default=0)
    applicant_department = models.CharField(max_length=150, blank=True, default="")
    applicant_role = models.CharField(max_length=64, blank=True, default="")
    applicant_is_director = models.BooleanField(default=False)

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
        max_length=36,
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
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_user_status_idx"),
            models.Index(fields=["status", "requested_start_date"], name="elm_status_start_idx"),
        ]

    def __str__(self):
        return (
            f"User {self.user_id}: {self.leave_type_code} leave "
            f"from {self.requested_start_date} to {self.requested_end_date} "
            f"({self.status})"
        )


class LeaveRequestEvent(models.Model):
    """Append-only status and decision history for employee inquiry."""
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="history"
    )
    event_type = models.CharField(max_length=48)
    from_status = models.CharField(max_length=36, blank=True, default="")
    to_status = models.CharField(max_length=36)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=("request", "created_at"), name="elm_request_history_idx")
        ]

    def __str__(self):
        return f"{self.request_id}: {self.event_type} -> {self.to_status}"
