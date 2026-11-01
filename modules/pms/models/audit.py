"""Immutable audit logs for all critical PMS actions (BR-PMS-121, 122)."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class PatentAuditLog(TimeStampedModel):
    """Immutable audit trail of all state transitions, reviews, uploads and decisions."""

    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    user_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=50)
    action_type = models.CharField(max_length=100, db_index=True)
    previous_state = models.CharField(max_length=50, blank=True)
    new_state = models.CharField(max_length=50, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "pms_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application", "-created_at"]),
            models.Index(fields=["action_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] User {self.user_id} {self.action_type}"
