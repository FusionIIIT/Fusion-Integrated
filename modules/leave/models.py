from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class LeaveRequest(TimeStampedModel):
    TYPE = [("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
            ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
            ("COL", "Commuted Leave"), ("VL", "Vacation Leave")]
    CL_PERIOD = [("full", "Full day"), ("first_half", "First half"),
                 ("second_half", "Second half")]
    STATUS = [("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
              ("cancelled", "Cancelled")]

    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=3, choices=TYPE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    cl_period = models.CharField(max_length=12, choices=CL_PERIOD, default="full")
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True)
    chargeable_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    charge_by_year = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewer_comment = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="leave_dates_ordered"),
        ]

    def clean(self):
        errors = {}
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date must be on or after start date."
        half_day = self.cl_period != "full"
        if half_day and (self.leave_type != "CL" or self.start_date != self.end_date):
            errors["cl_period"] = "Half-day periods are available only for one-day CL requests."
        if self.station_leave and not self.station_leave_details.strip():
            errors["station_leave_details"] = "Provide the Station Leave details."
        if not self.station_leave and self.station_leave_details.strip():
            errors["station_leave_details"] = "Details require Station Leave to be selected."
        if errors:
            raise ValidationError(errors)
        if self.employee_user_id and self.start_date and self.end_date:
            overlaps = LeaveRequest.objects.filter(
                employee_user_id=self.employee_user_id,
                start_date__lte=self.end_date, end_date__gte=self.start_date,
            ).exclude(status__in=("rejected", "withdrawn", "cancelled"))
            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)
            for other in overlaps:
                different_cl_halves = (
                    self.leave_type == other.leave_type == "CL"
                    and self.start_date == self.end_date == other.start_date == other.end_date
                    and self.cl_period in {"first_half", "second_half"}
                    and other.cl_period in {"first_half", "second_half"}
                    and self.cl_period != other.cl_period
                )
                if not different_cl_halves:
                    raise ValidationError("This request overlaps an existing active request.")


class LeaveCalendar(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("published", "Published"),
              ("replaced", "Replaced")]

    title = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    created_by_user_id = models.IntegerField()
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_calendar"
        constraints = [models.UniqueConstraint(
            fields=("status",), condition=Q(status="published"),
            name="leave_one_published_calendar")]

    def publish(self):
        if self.status != "draft":
            raise ValidationError("Only a draft calendar can be published.")
        self.status = "published"
        self.published_at = timezone.now()
        self.save(update_fields=("status", "published_at", "updated_at"))


class LeaveCalendarDay(models.Model):
    calendar = models.ForeignKey(LeaveCalendar, on_delete=models.CASCADE,
                                 related_name="days")
    date = models.DateField()
    is_closed = models.BooleanField(default=True)
    is_restricted_holiday = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_calendar_day"
        constraints = [models.UniqueConstraint(
            fields=("calendar", "date"), name="leave_calendar_date_unique")]




class LeaveBalance(TimeStampedModel):
    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=3, choices=LeaveRequest.TYPE)
    year = models.PositiveSmallIntegerField()
    available = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        db_table = "leave_balance"
        constraints = [models.UniqueConstraint(
            fields=("employee_user_id", "leave_type", "year"),
            name="leave_balance_employee_type_year_unique")]


class LeaveBalanceChange(models.Model):
    ACTION = [("adjustment", "Administrator adjustment"),
              ("approved", "Approved request deduction")]

    balance = models.ForeignKey(LeaveBalance, on_delete=models.PROTECT,
                                related_name="changes")
    leave_request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                      on_delete=models.PROTECT,
                                      related_name="balance_changes")
    action = models.CharField(max_length=16, choices=ACTION)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)
    actor_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_balance_change"
        ordering = ("-created_at",)

