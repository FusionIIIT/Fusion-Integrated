from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.elm.domain.leave import Category, Stage


class LeaveEmployeeState(models.Model):
    """Transaction mutex for one IAM employee; no cross-module identity FK."""
    employee_id = models.IntegerField(primary_key=True)

    class Meta:
        db_table = "elm_employee_state"


class LeaveBalance(TimeStampedModel):
    employee_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=[(c.value, c.value) for c in Category])
    year = models.PositiveSmallIntegerField()
    allotted = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    reserved = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=7, decimal_places=1, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(fields=("employee_id", "category", "year"),
                                    name="elm_balance_employee_category_year_uniq"),
            models.CheckConstraint(condition=Q(allotted__gte=0, reserved__gte=0, used__gte=0),
                                   name="elm_balance_values_nonnegative"),
            models.CheckConstraint(condition=Q(used__lte=F("allotted") - F("reserved")),
                                   name="elm_balance_not_overallocated"),
        ]
        indexes = [models.Index(fields=("employee_id", "year"), name="elm_balance_employee_year_idx")]


class HolidayCalendar(TimeStampedModel):
    name = models.CharField(max_length=120)
    is_effective = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        constraints = [models.UniqueConstraint(fields=("is_effective",),
                                               condition=Q(is_effective=True),
                                               name="elm_one_effective_calendar")]


class HolidayDate(TimeStampedModel):
    class Kind(models.TextChoices):
        CLOSED = "closed", "Closed holiday"
        RESTRICTED = "restricted", "Restricted holiday"

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="dates")
    day = models.DateField()
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=Kind.choices)

    class Meta:
        db_table = "elm_holiday_date"
        constraints = [models.UniqueConstraint(fields=("calendar", "day", "kind"),
                                               name="elm_calendar_date_kind_uniq")]
        indexes = [models.Index(fields=("calendar", "day"), name="elm_calendar_day_idx")]


class LeaveApprovalRoute(TimeStampedModel):
    employee_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=[(c.value, c.value) for c in Category])
    step_order = models.PositiveSmallIntegerField()
    stage = models.CharField(max_length=24, choices=[(s.value, s.value) for s in Stage])
    approver_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "elm_approval_route"
        constraints = [models.UniqueConstraint(fields=("employee_id", "category", "step_order"),
                                               name="elm_route_employee_category_step_uniq")]
        ordering = ("step_order",)
        indexes = [models.Index(fields=("approver_user_id", "employee_id", "category"),
                                name="elm_route_approver_idx")]


class LeaveApplication(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    employee_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=[(c.value, c.value) for c in Category])
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=8, blank=True,
                                choices=(("", "Full day"), ("first", "First half"),
                                         ("second", "Second half")))
    chargeable_days = models.DecimalField(max_digits=7, decimal_places=1)
    reason = models.CharField(max_length=2000)
    station_leave = models.BooleanField(default=False)
    station_details = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    current_step_order = models.PositiveSmallIntegerField(null=True, blank=True)
    current_stage = models.CharField(max_length=24, blank=True,
                                     choices=[("", "Complete"), *((s.value, s.value) for s in Stage)])
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        indexes = [
            models.Index(fields=("employee_id", "-created_at"), name="elm_application_employee_idx"),
            models.Index(fields=("status", "current_stage", "created_at"),
                         name="elm_application_queue_idx"),
            models.Index(fields=("start_date", "end_date", "status"),
                         name="elm_application_overlap_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                   name="elm_application_dates_ordered"),
            models.CheckConstraint(condition=Q(chargeable_days__gt=0),
                                   name="elm_application_days_positive"),
        ]


class LeaveCharge(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="charges")
    balance = models.ForeignKey(LeaveBalance, on_delete=models.PROTECT,
                                related_name="charges")
    days = models.DecimalField(max_digits=7, decimal_places=1)

    class Meta:
        db_table = "elm_leave_charge"
        constraints = [models.UniqueConstraint(fields=("application", "balance"),
                                               name="elm_charge_application_balance_uniq")]


class LeaveApplicationTransition(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=12)
    to_status = models.CharField(max_length=12)
    from_stage = models.CharField(max_length=24, blank=True)
    to_stage = models.CharField(max_length=24, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=24)
    note = models.CharField(max_length=2000, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_application_transition"
        ordering = ("at", "id")
