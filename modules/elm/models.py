"""ELM tables. People are plain user_id integers, never foreign keys (ADR-0013)."""
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel
from modules.elm.domain import balances as bal
from modules.elm.domain import leave_types as lt
from modules.elm.domain import workflow as wf

#: Kept so existing imports and the earlier tests keep working.
ANNUAL_ENTITLEMENT = {t: lt.ANNUAL_CREDIT[lt.STAFF].get(t, 0) for t in lt.ALL_TYPES}


class LeaveType(models.TextChoices):
    CL = lt.CL, "Casual Leave"
    RH = lt.RH, "Restricted Holiday"
    SCL = lt.SCL, "Special Casual Leave"
    EL = lt.EL, "Earned Leave"
    COL = lt.COL, "Commuted Leave"
    VL = lt.VL, "Vacation Leave"


class LeaveApplicationStatus(models.TextChoices):
    AWAITING_SUBSTITUTE = wf.AWAITING_SUBSTITUTE, "Awaiting substitute"
    SUBSTITUTE_DECLINED = wf.SUBSTITUTE_DECLINED, "Substitute declined"
    AWAITING_UNIT_HEAD = wf.AWAITING_UNIT_HEAD, "Awaiting Unit Head"
    AWAITING_ESTABLISHMENT = wf.AWAITING_ESTABLISHMENT, "Awaiting Establishment"
    AWAITING_FINAL = wf.AWAITING_FINAL, "Awaiting final sanction"
    AWAITING_DIRECTOR = wf.AWAITING_DIRECTOR, "Awaiting Director self-sanction"
    APPROVED = wf.APPROVED, "Approved"
    REJECTED = wf.REJECTED, "Rejected"
    WITHDRAWN = wf.WITHDRAWN, "Withdrawn"
    CANCELLED = wf.CANCELLED, "Cancelled"
    RESUMPTION_PENDING = wf.RESUMPTION_PENDING, "Resumption awaiting verification"
    COMPLETED = wf.COMPLETED, "Completed"


class HalfDay(models.TextChoices):
    NONE = lt.NO_HALF, "Whole day(s)"
    FIRST = lt.FIRST_HALF, "First half"
    SECOND = lt.SECOND_HALF, "Second half"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    year = models.IntegerField()
    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    entitled = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    #: EL/COL carried in from last year, plus EL converted from VL.
    carried_in = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    lapsed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    #: Set once year-end processing has run, so it can never run twice.
    closed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "leave_type"], name="elm_balance_unique"),
            models.CheckConstraint(condition=Q(used__gte=0), name="elm_balance_used_gte_0"),
        ]

    @property
    def remaining(self):
        return bal.remaining(self.entitled, self.carried_in, self.used, self.lapsed)

    def __str__(self):
        return f"{self.user_id} - {self.leave_type} balance for {self.year}"


class RestrictedHoliday(models.Model):
    year = models.IntegerField()
    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} on {self.date}"


class ClosedHoliday(models.Model):
    """A day the institute is closed; it does not count towards CL/SCL (BR-EL-011)."""

    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} on {self.date}"


class VacationPeriod(models.Model):
    """A published academic-calendar vacation, the only time VL may be taken."""

    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=Q(end_date__gte=F("start_date")), name="elm_vacation_dates_valid")]

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class ApplicationSource(models.TextChoices):
    ONLINE = "ONLINE", "Applied in ELM"
    OFFLINE = "OFFLINE", "Recorded from an offline sanction"


class LeaveApplication(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    applicant_kind = models.CharField(max_length=10, blank=True)
    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=10, choices=HalfDay.choices,
                                default=HalfDay.NONE)
    days = models.DecimalField(max_digits=6, decimal_places=2)
    special_purpose = models.TextField(blank=True)
    #: Decided by the sanctioning authority, never by the applicant (BR-EL-004).
    special_purpose_admissible = models.BooleanField(null=True, blank=True)
    medical_reference = models.CharField(max_length=200, blank=True)
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=200, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=40, choices=LeaveApplicationStatus.choices,
                              default=LeaveApplicationStatus.AWAITING_UNIT_HEAD)
    #: "CANCEL" while the cancellation of an approved leave is being decided.
    pending_action = models.CharField(max_length=10, blank=True)
    unit_head_recommendation = models.CharField(max_length=20, blank=True)
    is_director = models.BooleanField(default=False)

    decided_by = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)

    extends = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                related_name="extensions")
    resumed_on = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    restored_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    source = models.CharField(max_length=10, choices=ApplicationSource.choices,
                              default=ApplicationSource.ONLINE)
    offline_reference = models.CharField(max_length=120, blank=True)
    recorded_by = models.IntegerField(null=True, blank=True)

    waiting_since = models.DateTimeField(default=timezone.now)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="elm_app_owner_idx"),
            models.Index(fields=["status", "-created_at"], name="elm_app_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                   name="elm_app_dates_valid"),
            models.CheckConstraint(condition=Q(days__gt=0), name="elm_app_days_positive"),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.leave_type} from {self.start_date} to {self.end_date}"


class LeaveTransaction(models.Model):
    class Kind(models.TextChoices):
        DEDUCT = "DEDUCT", "Deduct"
        RESTORE = "RESTORE", "Restore"
        LAPSE = "LAPSE", "Lapse"
        CARRY_IN = "CARRY_IN", "Carried in"
        CONVERT_IN = "CONVERT_IN", "Converted from VL"

    balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE,
                                related_name="transactions")
    application = models.ForeignKey(LeaveApplication, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="transactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    days = models.DecimalField(max_digits=6, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.balance} - {self.kind} {self.days}"


class LeaveEvent(models.Model):
    """The audit trail: every move of an application, who made it, and why."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="events")
    action = models.CharField(max_length=30)
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.action}: {self.from_status} -> {self.to_status}"


class LeaveNotification(models.Model):
    """Written in the same transaction as the event that caused it (BR-EL-022, 032)."""

    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    #: A task owned by a role is addressed to everyone holding this permission.
    recipient_permission = models.CharField(max_length=64, blank=True, db_index=True)
    topic = models.CharField(max_length=40)
    message = models.CharField(max_length=300)
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, null=True,
                                    blank=True, related_name="notifications")
    dedupe_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.topic}: {self.message}"
