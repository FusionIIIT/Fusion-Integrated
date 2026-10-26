from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

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

