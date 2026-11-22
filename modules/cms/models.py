"""Complaint Management System tables.

CMS owns its records. Institute identities are IAM ids, kept as integers and
never as cross-module foreign keys.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Complaint(TimeStampedModel):
    STATUS = [
        (value, value.replace("_", " ").title())
        for value in ("submitted", "in_progress", "resolved", "rejected", "closed")
    ]
    PRIORITY = [(value, value.title()) for value in ("low", "medium", "high")]

    complaint_id = models.CharField(max_length=40, unique=True, db_index=True)
    complainant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=120, db_index=True)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS, default="submitted", db_index=True)
    priority = models.CharField(max_length=8, choices=PRIORITY, blank=True, db_index=True)
    assigned_handler_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    assignment_note = models.CharField(max_length=500, blank=True)
    resolution_details = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    closure_verifier = models.CharField(
        max_length=16,
        choices=[("complainant", "Complainant"), ("supervisor", "Supervisor")],
        blank=True,
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sla_reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    escalation_kind = models.CharField(
        max_length=12, choices=[("manual", "Manual"), ("automatic", "Automatic")], blank=True
    )

    class Meta:
        db_table = "cms_complaint"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["complainant_user_id", "-created_at"], name="cms_owner_recent_idx"
            ),
            models.Index(fields=["status", "priority", "-created_at"], name="cms_worklist_idx"),
        ]

    def __str__(self):
        return self.complaint_id


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    storage_key = models.CharField(max_length=128, unique=True)
    file_name = models.CharField(max_length=160)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    uploaded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "cms_complaint_attachment"


class ComplaintProgress(TimeStampedModel):
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="progress_updates"
    )
    actor_user_id = models.IntegerField()
    update_text = models.TextField()

    class Meta:
        db_table = "cms_complaint_progress"
        ordering = ["created_at", "id"]


class ComplaintHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cms_complaint_history"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.complaint_id}:{self.from_status}->{self.to_status}"


class ReopeningRequest(TimeStampedModel):
    DECISIONS = [("pending", "Pending"), ("approved", "Approved"), ("denied", "Denied")]
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="reopening_requests"
    )
    requested_by_user_id = models.IntegerField()
    request_reason = models.TextField()
    decision = models.CharField(max_length=12, choices=DECISIONS, default="pending", db_index=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cms_reopening_request"
        constraints = [
            models.UniqueConstraint(
                fields=["complaint"], condition=Q(decision="pending"), name="cms_one_pending_reopen"
            )
        ]


class ComplaintFeedback(TimeStampedModel):
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="feedback_entries"
    )
    submitted_by_user_id = models.IntegerField()
    feedback_text = models.TextField()

    class Meta:
        db_table = "cms_complaint_feedback"
        ordering = ["-created_at", "-id"]


class ComplaintAnnouncement(TimeStampedModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published_by_user_id = models.IntegerField()
    notify_users = models.BooleanField(default=False)
    published_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "cms_announcement"
        ordering = ["-published_at", "-id"]


class CmsNotificationEvent(models.Model):
    """CMS notification trigger record; delivery is platform infrastructure."""

    event_type = models.CharField(max_length=48, db_index=True)
    complaint = models.ForeignKey(
        Complaint,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notification_events",
    )
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cms_notification_event"

    def __str__(self):
        return f"{self.event_type} for complaint {self.complaint_id}"


class CmsRoleAssignment(TimeStampedModel):
    ROLE = [("handler", "Complaint Handler"), ("supervisor", "Complaint Supervisor")]
    role = models.CharField(max_length=16, choices=ROLE)
    user_id = models.IntegerField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "cms_role_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["role"], condition=Q(is_active=True), name="cms_one_active_role_holder"
            )
        ]


class CmsAuditEvent(models.Model):
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    action = models.CharField(max_length=48, db_index=True)
    object_type = models.CharField(max_length=40)
    object_id = models.CharField(max_length=48)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cms_audit_event"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action} {self.object_type}:{self.object_id}"
