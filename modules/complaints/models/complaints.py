"""Complaint lifecycle models and audit trail."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.complaints.domain.entities import (
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    ReopeningStatus,
)


class Complaint(TimeStampedModel):
    """Core complaint entity (CFR-CMS-001, AFR-CMS-001..029)."""

    complaint_id = models.CharField(max_length=32, unique=True, db_index=True)
    complainant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=64, db_index=True)
    description = models.TextField(max_length=4000)
    priority = models.CharField(
        max_length=16,
        choices=[(p.value, p.value.title()) for p in ComplaintPriority],
        default=ComplaintPriority.LOW.value,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value.title()) for s in ComplaintStatus],
        default=ComplaintStatus.SUBMITTED.value,
        db_index=True,
    )

    assigned_handler_id = models.IntegerField(null=True, blank=True, db_index=True)

    is_escalated = models.BooleanField(default=False, db_index=True)
    escalation_type = models.CharField(
        max_length=16,
        choices=[(e.value, e.value.title()) for e in EscalationType],
        blank=True,
    )
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True)

    resolution_details = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by_user_id = models.IntegerField(null=True, blank=True)

    sla_deadline = models.DateTimeField(null=True, blank=True)
    sla_reminder_sent = models.BooleanField(default=False)

    class Meta:
        db_table = "complaints_complaint"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="cmp_status_created_idx"),
            models.Index(fields=["complainant_user_id", "-created_at"], name="cmp_user_created_idx"),
            models.Index(
                fields=["assigned_handler_id"],
                condition=~Q(status__in=["closed", "rejected"]),
                name="cmp_handler_active_idx",
            ),
            models.Index(fields=["is_escalated", "-created_at"], name="cmp_escalated_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.complaint_id} ({self.status})"


class ComplaintAttachment(TimeStampedModel):
    """File attachments submitted with a complaint (AFR-CMS-005, BR-CMS-004, 005)."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    content_type = models.CharField(max_length=100)
    file_path = models.CharField(max_length=500)

    class Meta:
        db_table = "complaints_attachment"


class ComplaintAssignment(models.Model):
    """Handling setup and handler assignment record (AFR-CMS-011..015, BR-CMS-007..010)."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    handler_user_id = models.IntegerField(db_index=True)
    assigned_by_user_id = models.IntegerField()
    category = models.CharField(max_length=64, blank=True)
    priority = models.CharField(max_length=16, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_assignment"
        ordering = ["-assigned_at"]


class ProgressUpdate(models.Model):
    """Progress updates logged by complaint handlers (AFR-CMS-019, 021, BR-CMS-011)."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="progress_updates",
    )
    user_id = models.IntegerField()
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_progress_update"
        ordering = ["created_at"]


class StatusHistoryEntry(models.Model):
    """Append-only lifecycle status transition history (AFR-CMS-020, BR-CMS-011)."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by_user_id = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_status_history"
        ordering = ["created_at"]


class ClosureVerification(models.Model):
    """Verification for closure by User or Supervisor (AFR-CMS-027..029, BR-CMS-016, 017)."""

    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name="closure_verification",
    )
    verified_by_user_id = models.IntegerField()
    verifier_role = models.CharField(max_length=32)
    is_satisfied = models.BooleanField(default=True)
    comments = models.TextField(blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_closure_verification"


class ReopeningRequest(models.Model):
    """Reopening request for closed complaint and its supervisor review (AFR-CMS-030..034)."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="reopening_requests",
    )
    requested_by_user_id = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.value.title()) for s in ReopeningStatus],
        default=ReopeningStatus.PENDING.value,
        db_index=True,
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints_reopening_request"
        ordering = ["-requested_at"]


class ComplaintFeedback(models.Model):
    """Complainant feedback for resolved or closed complaint (AFR-CMS-035..037, BR-CMS-022)."""

    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    complainant_user_id = models.IntegerField()
    rating = models.IntegerField()
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_feedback"

