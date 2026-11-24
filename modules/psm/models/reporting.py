# Report schedules, generation logs, communication history, and audit trail (CFR-PSM-016..020).
from django.db import models

from core.db.mixins import TimeStampedModel


class ReportSchedule(TimeStampedModel):
    TYPES = [
        ("operational", "Operational"),
        ("procurement", "Procurement"),
        ("stock", "Stock"),
        ("financial", "Financial"),
    ]
    CADENCES = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")]

    name = models.CharField(max_length=160)
    report_type = models.CharField(max_length=20, choices=TYPES)
    filters = models.JSONField(default=dict, blank=True)
    cadence = models.CharField(max_length=16, choices=CADENCES)
    is_active = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField()
    created_by_role = models.CharField(max_length=64)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField()

    class Meta:
        db_table = "psm_report_schedule"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["is_active", "next_run_at"], name="psm_report_sched_due_idx"),
        ]


class ReportGenerationLog(models.Model):
    """Append-only log of every interactive and scheduled report run (AFR-PSM-082, BR-PSM-024)."""

    TRIGGERS = [("interactive", "Interactive"), ("scheduled", "Scheduled")]
    STATUS = [("succeeded", "Succeeded"), ("failed", "Failed"), ("blocked", "Blocked")]

    report_type = models.CharField(max_length=20)
    trigger_type = models.CharField(max_length=16, choices=TRIGGERS)
    schedule = models.ForeignKey(
        ReportSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs"
    )
    filters = models.JSONField(default=dict, blank=True)
    export_format = models.CharField(max_length=16, default="json")
    row_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS, default="succeeded")
    actor_user_id = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_report_log"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["report_type", "-created_at"], name="psm_report_log_type_idx"),
        ]

    def __str__(self) -> str:
        return f"report_log#{self.pk} {self.report_type}"


class PsmNotification(models.Model):
    """Append-only communication history for lifecycle and SLA alerts (BR-PSM-006, AFR-PSM-086)."""

    STATUS = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")]

    topic = models.CharField(max_length=64)
    dedupe_key = models.CharField(max_length=160, unique=True)
    recipient_user_id = models.IntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_notification"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient_user_id", "-created_at"], name="psm_notif_recip_idx"),
            models.Index(fields=["status", "created_at"], name="psm_notif_status_idx"),
        ]

    def __str__(self) -> str:
        return f"notif#{self.pk} {self.topic}"


class PsmAuditLog(models.Model):
    """Append-only audit trail for all material PSM actions (BR-PSM-021, AFR-PSM-087)."""

    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=40)
    target_id = models.IntegerField()
    from_state = models.CharField(max_length=32, blank=True)
    to_state = models.CharField(max_length=32, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_audit_log"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["target_type", "target_id", "-created_at"], name="psm_audit_target_idx"
            ),
            models.Index(fields=["-created_at"], name="psm_audit_recent_idx"),
        ]

    def __str__(self) -> str:
        return f"audit#{self.pk} {self.action}"
