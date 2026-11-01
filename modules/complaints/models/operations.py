"""Operational models: Announcements, CMS Role Assignments, and SLA Policies."""
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel
from modules.complaints.domain.entities import CMSRole, ComplaintPriority


class ComplaintAnnouncement(models.Model):
    """Complaint-related announcements (AFR-CMS-045..048, BR-CMS-030)."""

    AUDIENCE_CHOICES = [
        ("all", "All"),
        ("students", "Students"),
        ("faculty", "Faculty"),
        ("staff", "Staff"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    author_user_id = models.IntegerField()
    target_audience = models.CharField(max_length=32, choices=AUDIENCE_CHOICES, default="all")
    published_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints_announcement"
        ordering = ["-published_at"]

    def is_active(self) -> bool:
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class CMSRoleAssignment(TimeStampedModel):
    """CMS-specific operational & supervisory role assignments (AFR-CMS-064..068, BR-CMS-035..037).

    Guarantees exactly one active Complaint Handler and one active Complaint Supervisor.
    """

    ROLE_CHOICES = [
        (CMSRole.COMPLAINT_HANDLER.value, "Complaint Handler"),
        (CMSRole.COMPLAINT_SUPERVISOR.value, "Complaint Supervisor"),
    ]

    user_id = models.IntegerField(db_index=True)
    role_name = models.CharField(max_length=32, choices=ROLE_CHOICES, db_index=True)
    assigned_by_user_id = models.IntegerField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "complaints_role_assignment"
        ordering = ["-valid_from"]

    def __str__(self) -> str:
        return f"{self.role_name}: user {self.user_id} (active={self.is_active})"


class SLAPolicy(models.Model):
    """SLA thresholds associated with priority levels (AFR-CMS-041, 042, BR-CMS-026, 027)."""

    priority = models.CharField(
        max_length=16,
        choices=[(p.value, p.value.title()) for p in ComplaintPriority],
        unique=True,
    )
    duration_hours = models.IntegerField(default=72)
    reminder_before_hours = models.IntegerField(default=12)

    class Meta:
        db_table = "complaints_sla_policy"

    def __str__(self) -> str:
        return f"SLA: {self.priority} -> {self.duration_hours}h (reminder: {self.reminder_before_hours}h before)"

