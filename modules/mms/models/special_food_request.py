"""Special food request (BR-MMS-028/029/030/031; UC-019/020/021/029;
BW-MMS-11..15, CW-MMS-05)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class SpecialFoodRequest(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("served", "Served"),
        ("cancelled", "Cancelled"),
    ]

    reason = models.TextField()
    requested_date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=STATUS, default="requested")
    #: submitted_at + institution-defined decision period (policy row).
    decision_due_at = models.DateTimeField(db_index=True, null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "mms_special_food_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="sf_student_status_idx"),
            models.Index(fields=["status", "decision_due_at"], name="special_food_due_idx"),
            models.Index(fields=["requested_date"], name="sf_req_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(status__in=("served", "cancelled", "rejected")) | Q(decided_at__isnull=False)
                ),
                name="special_food_terminal_decided",
            ),
            models.CheckConstraint(
                condition=(~Q(status="requested") | Q(decided_at__isnull=True)),
                name="special_food_requested_undecided",
            ),
        ]

    def __str__(self) -> str:
        return f"special_food:{self.pk}:{self.status}"
