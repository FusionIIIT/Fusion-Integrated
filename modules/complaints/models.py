"""Database models for the Complaint Management System."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.complaints.domain.state_machine import (
    ClosureVerification,
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    ReopeningStatus,
)


class ComplaintCategory(TimeStampedModel):
    """Institutional complaint category (e.g., Electrical, Plumbing, Network, Hostel)."""

    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    default_sla_hours = models.PositiveIntegerField(default=48)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Complaint Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Complaint(TimeStampedModel):
    """Central complaint record tracked across its full lifecycle."""

    complaint_id = models.CharField(max_length=32, unique=True, db_index=True)
    complainant_user_id = models.IntegerField(db_index=True)
    category = models.ForeignKey(
        ComplaintCategory,
        on_delete=models.PROTECT,
        related_name="complaints",
    )
    location = models.CharField(max_length=160)
    description = models.TextField(max_length=4000)

    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ComplaintStatus],
        default=ComplaintStatus.SUBMITTED.value,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=[(p.value, p.value) for p in ComplaintPriority],
        default=ComplaintPriority.MEDIUM.value,
    )

    assigned_worker_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_worker_name = models.CharField(max_length=120, blank=True)

    resolution_details = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    verification_required = models.CharField(
        max_length=20,
        choices=[(v.value, v.value) for v in ClosureVerification],
        default=ClosureVerification.NONE.value,
    )

    is_escalated = models.BooleanField(default=False, db_index=True)
    escalation_type = models.CharField(
        max_length=20,
        choices=[(e.value, e.value) for e in EscalationType],
        default=EscalationType.NONE.value,
    )
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_remarks = models.TextField(blank=True)

    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    reopening_status = models.CharField(
        max_length=20,
        choices=[(r.value, r.value) for r in ReopeningStatus],
        default=ReopeningStatus.NONE.value,
    )
    reopening_reason = models.TextField(blank=True)
    reopening_review_remarks = models.TextField(blank=True)

    sla_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    sla_reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="complaint_status_recent_idx"),
            models.Index(fields=["complainant_user_id", "-created_at"], name="complaint_user_recent_idx"),
            models.Index(fields=["is_escalated", "-created_at"], name="complaint_escalated_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.complaint_id} ({self.status})"


class ComplaintAttachment(TimeStampedModel):
    """File evidence supporting a complaint submission."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="complaints/attachments/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by_user_id = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.file_name} for {self.complaint.complaint_id}"


class ComplaintTransition(TimeStampedModel):
    """Append-only audit trail of complaint state transitions and updates."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.complaint.complaint_id}: {self.from_status} -> {self.to_status}"


class ComplaintFeedback(TimeStampedModel):
    """Complainant satisfaction rating and feedback after resolution/closure."""

    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    complainant_user_id = models.IntegerField(db_index=True)
    rating = models.PositiveSmallIntegerField()  # 1 to 5
    comments = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Rating {self.rating} for {self.complaint.complaint_id}"


class ComplaintAnnouncement(TimeStampedModel):
    """Notices published by Handler or Supervisor to institutional users."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(
        ComplaintCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="announcements",
    )
    author_user_id = models.IntegerField()
    author_name = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-pinned", "-created_at"]

    def __str__(self) -> str:
        return self.title


class CmsRoleAssignment(TimeStampedModel):
    """Time-bound assignment of Complaint Handler and Supervisor roles.

    Enforces exactly one active holder per role type at any given time.
    """

    ROLE_HANDLER = "handler"
    ROLE_SUPERVISOR = "supervisor"
    ROLE_CHOICES = [
        (ROLE_HANDLER, "Complaint Handler"),
        (ROLE_SUPERVISOR, "Complaint Supervisor"),
    ]

    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    user_id = models.IntegerField(db_index=True)
    assigned_by_user_id = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.get_role_type_display()}: User {self.user_id} (active: {self.is_active})"
