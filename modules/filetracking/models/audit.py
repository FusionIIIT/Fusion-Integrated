"""FileAuditLog model for File Tracking System."""

from django.db import models

from core.db.mixins import TimeStampedModel


class FileAuditLog(TimeStampedModel):
    file_id = models.IntegerField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=64, db_index=True)
    actor_user_id = models.IntegerField(db_index=True)
    actor_designation = models.CharField(max_length=128)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "filetracking_audit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["file_id", "-created_at"],
                name="idx_fts_audit_file_created",
            ),
            models.Index(
                fields=["actor_user_id", "-created_at"],
                name="idx_fts_audit_actor_created",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action} by User #{self.actor_user_id} at {self.created_at}"
