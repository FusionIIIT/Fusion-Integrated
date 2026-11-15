"""Decision and follow-up records for leave requests."""

from django.db import models

from core.db.mixins import TimeStampedModel


class ApprovalRecord(TimeStampedModel):
    OUTCOMES = [
        ("recommended", "Recommended"),
        ("not_recommended", "Not recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    application = models.ForeignKey(
        "leave_elm.LeaveApplication", on_delete=models.CASCADE, related_name="approval_records"
    )
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=80, blank=True)
    outcome = models.CharField(max_length=20, choices=OUTCOMES)
    comments = models.TextField(blank=True)

    class Meta:
        db_table = "leave_approval_record"
        ordering = ["created_at"]


class CancellationRecord(TimeStampedModel):
    STATUS = [
        ("pending", "Pending"),
        ("awaiting_establishment", "Awaiting Establishment"),
        ("awaiting_sanction", "Awaiting Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    application = models.ForeignKey(
        "leave_elm.LeaveApplication", on_delete=models.PROTECT, related_name="cancellations"
    )
    requested_by_user_id = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS, default="pending")
    assigned_role = models.CharField(max_length=80, default="unit_head")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_cancellation_record"


class ExtensionRecord(TimeStampedModel):
    STATUS = [
        ("pending", "Pending"),
        ("awaiting_substitute", "Awaiting Substitute"),
        ("applicant_action_required", "Applicant Action Required"),
        ("awaiting_establishment", "Awaiting Establishment"),
        ("awaiting_sanction", "Awaiting Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    application = models.ForeignKey(
        "leave_elm.LeaveApplication", on_delete=models.PROTECT, related_name="extensions"
    )
    requested_by_user_id = models.IntegerField()
    additional_starts_on = models.DateField()
    additional_ends_on = models.DateField()
    additional_days = models.DecimalField(max_digits=7, decimal_places=2)
    additional_days_by_year = models.JSONField(default=dict, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS, default="pending")
    assigned_role = models.CharField(max_length=80, default="unit_head")
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=12, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_extension_record"


class ResumptionRecord(TimeStampedModel):
    STATUS = [("submitted", "Submitted"), ("reviewed", "Reviewed")]

    application = models.ForeignKey(
        "leave_elm.LeaveApplication", on_delete=models.PROTECT, related_name="resumptions"
    )
    user_id = models.IntegerField()
    actual_resumption_date = models.DateField()
    details = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="submitted")
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    actual_leave_days = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    actual_leave_end = models.DateField(null=True, blank=True)
    actual_days_by_year = models.JSONField(default=dict, blank=True)
    assigned_role = models.CharField(max_length=80, default="registrar")

    class Meta:
        db_table = "leave_resumption_record"
