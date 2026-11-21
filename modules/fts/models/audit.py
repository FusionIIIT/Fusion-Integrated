"""FTS Audit Log model (CFR-FTS-010, BR-FTS-011)."""
from django.db import models


class FTSAuditLog(models.Model):
    file = models.ForeignKey(
        "fts.FTSFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=128, blank=True, default="")
    action_type = models.CharField(max_length=64, db_index=True)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "fts_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action_type", "timestamp"], name="idx_fts_audit_act_ts"),
            models.Index(fields=["actor_id", "timestamp"], name="idx_fts_audit_actor_ts"),
        ]

    def __str__(self) -> str:
        return f"{self.action_type} by {self.actor_id} at {self.timestamp}"
