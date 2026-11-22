from django.db import models


class AuditEvent(models.Model):
    event_type = models.CharField(max_length=60)
    actor_user_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=50)
    target_model = models.CharField(max_length=50)
    target_id = models.BigIntegerField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badms_audit_event"
        indexes = [
            models.Index(fields=["event_type", "-timestamp"], name="idx_badms_audit_type_time"),
            models.Index(fields=["actor_user_id", "-timestamp"], name="idx_badms_audit_actor_time"),
            models.Index(fields=["department", "-timestamp"], name="idx_badms_audit_dept_time"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} at {self.timestamp}"
