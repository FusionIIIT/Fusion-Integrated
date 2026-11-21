from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.accounting import Outcome, Reason
from modules.leave.domain.counting import Half
from modules.leave.domain.workflow import PENDING, State
from modules.leave.models.configuration import CATEGORY_CHOICES

_PENDING = sorted(s.value for s in PENDING)


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """One application, cancellation or extension. Never edited after submission (BR-EL-034)."""

    NEW, CANCELLATION, EXTENSION = "new", "cancellation", "extension"
    ONLINE, OFFLINE = "online", "offline"

    kind = models.CharField(max_length=12, default=NEW, choices=[
        (NEW, "New"), (CANCELLATION, "Cancellation"), (EXTENSION, "Extension")])
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="children")
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=6, default=Half.FULL.value,
                            choices=[(h.value, h.value) for h in Half])
    days = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True)
    medical_evidence_ref = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, db_index=True,
                              choices=[(s.value, s.value) for s in State])
    status_changed_at = models.DateTimeField(default=timezone.now)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    establishment_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    unit_head_final = models.BooleanField(default=False)
    director_self = models.BooleanField(default=False)
    recommendation = models.CharField(max_length=16, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=8, default=ONLINE,
                              choices=[(ONLINE, "Online"), (OFFLINE, "Offline")])
    offline_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "leave_request"
        indexes = [models.Index(fields=["user_id", "status"], name="leave_req_user_status"),
                   models.Index(fields=["status", "status_changed_at"],
                                name="leave_req_status_since")]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="leave_request_ordered"),
            models.CheckConstraint(condition=models.Q(days__gt=0) | models.Q(kind="cancellation"),
                                   name="leave_request_positive_days"),
            models.UniqueConstraint(fields=["parent"], name="leave_one_open_cancellation",
                                    condition=models.Q(kind="cancellation", status__in=_PENDING)),
            models.UniqueConstraint(fields=["parent"], name="leave_one_open_extension",
                                    condition=models.Q(kind="extension", status__in=_PENDING)),
        ]


class LeaveTransition(models.Model):
    """Append-only history; what the employee reads as status (PS §7)."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="transitions")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    event = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_transition"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"#{self.request_id} {self.from_status}->{self.to_status}"


class LedgerEntry(UserScopedModel):
    """The balance is the sum; corrections are new rows, never edits."""

    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    year = models.PositiveSmallIntegerField()
    days = models.DecimalField(max_digits=6, decimal_places=1)
    reason = models.CharField(max_length=20, choices=[(r.value, r.value) for r in Reason])
    request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                on_delete=models.PROTECT, related_name="ledger")
    note = models.CharField(max_length=255, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=80, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_ledger_entry"
        indexes = [models.Index(fields=["user_id", "year", "category"],
                                name="leave_ledger_lookup")]


class Resumption(TimeStampedModel):
    PENDING, REVIEWED = "pending", "reviewed"

    leave = models.OneToOneField(LeaveRequest, on_delete=models.PROTECT,
                                 related_name="resumption")
    actual_date = models.DateField()
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=10, default=PENDING,
                              choices=[(PENDING, "Pending"), (REVIEWED, "Reviewed")])
    outcome = models.CharField(max_length=8, blank=True,
                               choices=[(o.value, o.value) for o in Outcome])
    adjustment_days = models.DecimalField(max_digits=5, decimal_places=1,
                                          null=True, blank=True)
    reviewer_user_id = models.IntegerField()
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_resumption"


class LeaveNotification(UserScopedModel):
    """In-app notices; `idempotency_key` keeps an SLA reminder to once per state entry."""

    kind = models.CharField(max_length=16)
    message = models.CharField(max_length=300)
    request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                on_delete=models.CASCADE)
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_notification"
