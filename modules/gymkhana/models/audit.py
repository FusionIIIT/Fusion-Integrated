"""The module's audit trail: who did what to which row, as ids and codes only."""
from django.db import models


class AuditEvent(models.Model):
    action = models.CharField(max_length=60)
    object_type = models.CharField(max_length=40)
    object_id = models.BigIntegerField()
    actor_user_id = models.IntegerField(null=True, blank=True)
    club_id = models.BigIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_audit_event"

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"
