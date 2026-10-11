from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Recess Half"),
        ("SCL", "Sick Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Compensatory Leave"),
        ("VL", "Voluntary Leave"),
    ]

    applicant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    reason = models.TextField()
    station_leave_details = models.TextField(blank=True, null=True)
    substitute_user_id = models.IntegerField(db_index=True, null=True, blank=True)
    status = models.CharField(max_length=20)

    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"


class LeaveDecision(TimeStampedModel, UserScopedModel):
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    actor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=50)
    remark = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Leave Decision"
        verbose_name_plural = "Leave Decisions"
