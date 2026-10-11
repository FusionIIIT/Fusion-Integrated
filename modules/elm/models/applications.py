"""Leave applications and their append-only audit (BR-03, BR-05, BR-15)."""
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """One request. `user_id` is the IAM id, never a foreign key."""

    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    ACTIVE_STATUSES = ("pending", "approved")
    HALF_DAY_PARTS = [("first", "First half"), ("second", "Second half")]

    leave_type = models.ForeignKey("elm.LeaveType", on_delete=models.PROTECT,
                                   related_name="applications")
    start_date = models.DateField()
    end_date = models.DateField()
    #: Frozen at submission from domain.policy.count_days (BR-01).
    days = models.DecimalField(max_digits=5, decimal_places=1)
    is_half_day = models.BooleanField(default=False)
    half_day_part = models.CharField(max_length=6, choices=HALF_DAY_PARTS,
                                     blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-start_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                   name="leave_application_dates_ordered"),
            models.CheckConstraint(condition=Q(days__gt=0),
                                   name="leave_application_days_positive"),
            # The database refuses a second active request starting the same day;
            # ranges beyond that are refused by the service.
            models.UniqueConstraint(
                fields=["user_id", "start_date"],
                condition=Q(status__in=["pending", "approved"]),
                name="leave_application_one_active_per_day"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"],
                         name="leave_app_user_status_idx"),
            models.Index(fields=["status", "start_date"],
                         name="leave_app_status_start_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.status}"

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES


class LeaveEvent(models.Model):
    """Append-only audit of every state change and its actor (BR-15)."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="events")
    from_status = models.CharField(max_length=16)
    to_status = models.CharField(max_length=16)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_event"
        ordering = ["at", "id"]
        indexes = [
            models.Index(fields=["application", "at"],
                         name="leave_event_app_idx"),
        ]

    def __str__(self) -> str:
        return f"event#{self.pk} {self.from_status}->{self.to_status}"
