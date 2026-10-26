from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveRequest(TimeStampedModel):
    TYPE = [("annual", "Annual"), ("sick", "Sick"), ("personal", "Personal")]
    STATUS = [("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected"), ("cancelled", "Cancelled")]

    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=16, choices=TYPE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
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
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})
        if self.employee_user_id and self.start_date and self.end_date:
            overlaps = LeaveRequest.objects.filter(
                employee_user_id=self.employee_user_id,
                start_date__lte=self.end_date, end_date__gte=self.start_date,
            ).exclude(status__in=("rejected", "cancelled"))
            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)
            if overlaps.exists():
                raise ValidationError("This request overlaps an existing active request.")

