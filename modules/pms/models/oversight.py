"""Settings versions, audit, escalations, alerts, notifications and saved reports."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import deadlines as dl
from modules.pms.domain import reports as rp
from modules.pms.models.applications import Application
from modules.pms.models.base import AppendOnly, choices


class PmsPolicy(AppendOnly):
    """One published settings version; the latest one in effect applies (Step 2.8)."""

    version = models.PositiveIntegerField(unique=True)
    effective_from = models.DateTimeField()
    payload = models.JSONField()
    published_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["-effective_from", "-version"],
                                name="pms_policy_effective_idx")]


class AuditEntry(AppendOnly):
    """BR-PMS-121 / 122: who did what, when, to which application, from and to which state."""

    at = models.DateTimeField(auto_now_add=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=64)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, null=True,
                                    blank=True, related_name="audit_entries")
    object_type = models.CharField(max_length=40, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    from_state = models.CharField(max_length=30, blank=True)
    to_state = models.CharField(max_length=30, blank=True)
    details = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["application", "-at"], name="pms_audit_app_idx"),
            models.Index(fields=["actor_user_id", "-at"], name="pms_audit_actor_idx"),
            models.Index(fields=["action", "-at"], name="pms_audit_action_idx"),
        ]


ESCALATION_KINDS = ("missed_review", "missed_revision", "missed_office_action",
                    "missed_maintenance", "no_eligible_director", "no_eligible_attorney",
                    "conflicted_admin", "budget_threshold", "inactive_renewal_director")
ESCALATION_STATUSES = ("open", "routed", "resolved")


class Escalation(TimeStampedModel):
    kind = models.CharField(max_length=28, choices=choices(ESCALATION_KINDS))
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="escalations")
    subject_id = models.IntegerField()
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=choices(ESCALATION_STATUSES),
                              default="open")
    note = models.TextField(blank=True)
    handled_by_user_id = models.IntegerField(null=True, blank=True)
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["kind", "subject_id"],
                                               condition=Q(status="open"),
                                               name="pms_escalation_open_once")]
        indexes = [models.Index(fields=["status", "-created_at"], name="pms_escalation_open_idx")]


class DeadlineAlert(AppendOnly):
    """BR-PMS-101..103: one row per alert sent, so a rerun cannot send it twice."""

    kind = models.CharField(max_length=16, choices=choices(dl.KINDS))
    subject_id = models.IntegerField()
    deadline = models.DateField()
    offset_days = models.PositiveIntegerField()
    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["kind", "subject_id", "deadline", "offset_days"], name="pms_alert_once")]


class Notification(TimeStampedModel):
    """The email outbox; delivery is the mail backend's job (BR-PMS-116)."""

    topic = models.CharField(max_length=64)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=choices(("pending", "sent", "failed")),
                              default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"],
                                name="pms_notification_pending_idx")]


class ReportDefinition(TimeStampedModel):
    owner_user_id = models.IntegerField()
    owner_role = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    report_type = models.CharField(max_length=20, choices=choices(rp.TYPES))
    filters = models.JSONField(default=dict)
    columns = models.JSONField(default=list)
    schedule = models.CharField(max_length=10, choices=choices(rp.SCHEDULES), default="none")
    active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner_user_id", "-created_at"], name="pms_reportdef_owner_idx"),
            models.Index(fields=["schedule"], name="pms_reportdef_due_idx",
                         condition=Q(active=True) & ~Q(schedule="none")),
        ]


class ReportRun(AppendOnly):
    definition = models.ForeignKey(ReportDefinition, on_delete=models.PROTECT,
                                   related_name="runs")
    period = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["definition", "period"],
                                               name="pms_reportrun_once")]
