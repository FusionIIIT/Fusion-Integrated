"""Complaint domain records. IAM identities are opaque integer ids."""

import uuid

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Complaint(TimeStampedModel):
    STATUS = [
        (v, v.replace("_", " ").title())
        for v in ("submitted", "in_progress", "resolved", "rejected", "closed")
    ]
    PRIORITY = [(v, v.title()) for v in ("low", "medium", "high")]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    complainant_user_id = models.PositiveIntegerField(db_index=True)
    category = models.TextField()
    description = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS, default="submitted", db_index=True)
    priority = models.CharField(max_length=8, choices=PRIORITY, blank=True, default="")
    assigned_to_user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sla_reminded_at = models.DateTimeField(null=True, blank=True)
    verification_required = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    resolution_details = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "complaints_complaint"
        ordering = ("-submitted_at",)
        indexes = [
            models.Index(
                fields=("complainant_user_id", "-submitted_at"), name="cms_complainant_recent_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=("submitted", "in_progress", "resolved", "rejected", "closed")
                ),
                name="cms_complaint_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(priority__in=("low", "medium", "high"))
                | (Q(priority="") & Q(assigned_to_user_id__isnull=True)),
                name="cms_complaint_priority_valid",
            ),
            models.CheckConstraint(
                condition=~Q(status="resolved") | ~Q(resolution_details=""),
                name="cms_resolved_has_details",
            ),
            models.CheckConstraint(
                condition=~Q(status="rejected") | ~Q(rejection_reason=""),
                name="cms_rejected_has_reason",
            ),
        ]

    def __str__(self):
        return str(self.reference)


class ComplaintHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name="history")
    event = models.CharField(max_length=32)
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    actor_user_id = models.PositiveIntegerField(null=True, blank=True)
    actor_kind = models.CharField(max_length=24)
    details = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "complaints_history"
        ordering = ("occurred_at", "pk")
        indexes = [
            models.Index(fields=("complaint", "occurred_at"), name="cms_history_complaint_idx")
        ]

    def __str__(self):
        return f"{self.complaint_id}:{self.event}"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name="attachments")
    storage_key = models.CharField(max_length=64, unique=True)
    original_name = models.CharField(max_length=120)
    content_type = models.CharField(max_length=160)
    byte_size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    uploaded_by_user_id = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_attachment"
        indexes = [
            models.Index(fields=("complaint", "uploaded_at"), name="cms_attachment_complaint_idx")
        ]

    def __str__(self):
        return self.original_name


class ReopeningRequest(TimeStampedModel):
    STATUS = [(v, v.title()) for v in ("pending", "approved", "denied")]
    complaint = models.ForeignKey(
        Complaint, on_delete=models.PROTECT, related_name="reopening_requests"
    )
    requested_by_user_id = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    reviewed_by_user_id = models.PositiveIntegerField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints_reopening_request"
        constraints = [
            models.UniqueConstraint(
                fields=("complaint",), condition=Q(status="pending"), name="cms_one_pending_reopen"
            )
        ]
        indexes = [models.Index(fields=("status", "created_at"), name="cms_reopen_pending_idx")]


class Feedback(TimeStampedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name="feedback")
    submitted_by_user_id = models.PositiveIntegerField()
    message = models.TextField()

    class Meta:
        db_table = "complaints_feedback"
        constraints = [
            models.UniqueConstraint(
                fields=("complaint", "submitted_by_user_id"), name="cms_feedback_one_per_user"
            )
        ]


class Escalation(models.Model):
    SOURCE = [("manual", "Manual"), ("sla", "SLA")]
    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name="escalations")
    source = models.CharField(max_length=8, choices=SOURCE)
    escalated_by_user_id = models.PositiveIntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    escalated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_escalation"
        constraints = [
            models.UniqueConstraint(
                fields=("complaint", "source"), name="cms_escalation_source_once"
            )
        ]
        indexes = [models.Index(fields=("escalated_at",), name="cms_escalation_recent_idx")]

    def __str__(self):
        return f"{self.complaint_id}:{self.source}"


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published_by_user_id = models.PositiveIntegerField()
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "complaints_announcement"
        ordering = ("-published_at",)


class NotificationOutbox(TimeStampedModel):
    STATUS = [(v, v.title()) for v in ("pending", "sending", "sent", "failed")]
    topic = models.CharField(max_length=64)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.PositiveIntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints_notification_outbox"
        indexes = [models.Index(fields=("status", "created_at"), name="cms_outbox_pending_idx")]


class IdempotencyRecord(TimeStampedModel):
    user_id = models.PositiveIntegerField()
    key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    response_body = models.JSONField(null=True, blank=True)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "complaints_idempotency_record"
        constraints = [
            models.UniqueConstraint(fields=("user_id", "key"), name="cms_idempotency_user_key")
        ]
