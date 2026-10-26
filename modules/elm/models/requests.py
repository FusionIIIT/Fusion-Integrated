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
    status = models.CharField(max_length=64, choices=[
        ("Draft / Not Submitted", "Draft / Not Submitted"),
        ("Awaiting Substitute Response", "Awaiting Substitute Response"),
        ("Awaiting Director Self-Sanction", "Awaiting Director Self-Sanction"),
        ("Awaiting Unit Head Review", "Awaiting Unit Head Review"),
        ("Applicant Action Required", "Applicant Action Required"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Awaiting Establishment Routing", "Awaiting Establishment Routing"),
        ("Awaiting Final Sanction Decision", "Awaiting Final Sanction Decision"),
        ("Withdrawn", "Withdrawn"),
        ("Approved / Not Started", "Approved / Not Started"),
        ("Cancellation Pending — Unit Head Review", "Cancellation Pending — Unit Head Review"),
        ("Cancelled", "Cancelled"),
        ("deducted balance restored/adjusted", "deducted balance restored/adjusted"),
        ("Approved / Unchanged", "Approved / Unchanged"),
        ("Cancellation Pending — Establishment", "Cancellation Pending — Establishment"),
        ("Cancellation Pending — Final Decision", "Cancellation Pending — Final Decision"),
        ("Ongoing EL/COL/VL", "Ongoing EL/COL/VL"),
        ("Awaiting Extension Substitute Response", "Awaiting Extension Substitute Response"),
        ("Awaiting Extension Unit Head Review", "Awaiting Extension Unit Head Review"),
        ("Extension Applicant Action Required", "Extension Applicant Action Required"),
        ("Extension Pending — Establishment", "Extension Pending — Establishment"),
        ("Extension Pending — Final Decision", "Extension Pending — Final Decision"),
        ("Extended Leave in Effect — Incremental Period Posted", "Extended Leave in Effect — Incremental Period Posted"),
        ("Original Ongoing Leave Unchanged", "Original Ongoing Leave Unchanged"),
        ("Extension Request Withdrawn — Original Leave Unchanged", "Extension Request Withdrawn — Original Leave Unchanged"),
        ("Returned from EL/COL/VL", "Returned from EL/COL/VL"),
        ("Resumption Review Pending", "Resumption Review Pending"),
        ("Resumption Reviewed — No Adjustment", "Resumption Reviewed — No Adjustment"),
        ("Resumption Reviewed — Early Return Synchronized", "Resumption Reviewed — Early Return Synchronized"),
        ("Resumption Reviewed — Late Return Synchronized", "Resumption Reviewed — Late Return Synchronized"),
    ])

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
