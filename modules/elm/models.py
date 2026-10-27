"""ELM-owned leave requests and their workflow record.

IAM identities are referenced by integer IDs. ELM does not own employee
identity, organizational hierarchy, or leave balances.
"""

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    class LeaveType(models.TextChoices):
        CL = "CL", "CL"
        RH = "RH", "RH"
        SCL = "SCL", "SCL"
        EL = "EL", "EL"
        COL = "COL", "COL"
        VL = "VL", "VL"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE", "Pending substitute"
        APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED", "Applicant action required"
        PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD", "Pending Unit Head"
        PENDING_ESTABLISHMENT = "PENDING_ESTABLISHMENT", "Pending establishment"
        PENDING_FINAL_DECISION = "PENDING_FINAL_DECISION", "Pending final decision"
        PENDING_DIRECTOR_SANCTION = "PENDING_DIRECTOR_SANCTION", "Pending Director sanction"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        CANCELLED = "CANCELLED", "Cancelled"

    class HalfDay(models.TextChoices):
        FIRST = "FIRST", "First half"
        SECOND = "SECOND", "Second half"

    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    half_day = models.CharField(  # noqa: DJ001 — NULL represents a full-day request
        max_length=6, choices=HalfDay.choices, null=True, blank=True
    )
    chargeable_days = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="elm_leave_dates_ordered",
            ),
            models.CheckConstraint(
                condition=Q(chargeable_days__isnull=True) | Q(chargeable_days__gte=0),
                name="elm_chargeable_days_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="elm_request_user_created_idx"),
            models.Index(
                fields=["status", "start_date", "end_date"],
                name="elm_request_status_dates_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"ELM-{self.pk} ({self.leave_type})"


class LeaveWorkflowAction(models.Model):
    """Append-only record of an attempted successful workflow transition."""

    class Action(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        SUBSTITUTE_NOMINATED = "SUBSTITUTE_NOMINATED", "Substitute nominated"
        SUBSTITUTE_ACCEPTED = "SUBSTITUTE_ACCEPTED", "Substitute accepted"
        SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED", "Substitute declined"
        UNIT_HEAD_RECOMMENDED = "UNIT_HEAD_RECOMMENDED", "Unit Head recommended"
        UNIT_HEAD_NOT_RECOMMENDED = "UNIT_HEAD_NOT_RECOMMENDED", "Unit Head not recommended"
        ESTABLISHMENT_PROCESSED = "ESTABLISHMENT_PROCESSED", "Establishment processed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="workflow_actions"
    )
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    action = models.CharField(max_length=32, choices=Action.choices)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=80, blank=True)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_workflow_action"
        ordering = ["at", "id"]
        indexes = [
            models.Index(fields=["request", "at"], name="elm_action_request_time_idx"),
        ]

    def __str__(self) -> str:
        return f"ELM-{self.request_id}: {self.action}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Workflow actions are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Workflow actions are append-only.")


class LeaveApprovalStep(models.Model):
    class StepStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        SKIPPED = "SKIPPED", "Skipped"

    class Decision(models.TextChoices):
        RECOMMENDED = "RECOMMENDED", "Recommended"
        NOT_RECOMMENDED = "NOT_RECOMMENDED", "Not recommended"
        PROCESSED = "PROCESSED", "Processed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="approval_steps"
    )
    sequence = models.PositiveSmallIntegerField()
    role_code = models.CharField(max_length=48)
    assigned_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=StepStatus.choices, default=StepStatus.PENDING)
    decision = models.CharField(  # noqa: DJ001 — NULL means the step has no decision yet
        max_length=20, choices=Decision.choices, null=True, blank=True
    )
    reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_approval_step"
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "sequence"], name="elm_approval_step_unique"
            ),
        ]
        indexes = [
            models.Index(
                fields=["assigned_user_id", "status"], name="elm_step_assignee_status_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"ELM-{self.request_id}: step {self.sequence} ({self.role_code})"


class SubstituteAssignment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="substitute_assignments"
    )
    sequence = models.PositiveSmallIntegerField()
    nominee_user_id = models.IntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    nominated_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_substitute_assignment"
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "sequence"], name="elm_substitute_sequence_unique"
            ),
        ]
        indexes = [
            models.Index(
                fields=["nominee_user_id", "status"], name="elm_substitute_user_status_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"ELM-{self.request_id}: substitute {self.nominee_user_id}"
