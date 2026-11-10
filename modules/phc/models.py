from django.db import models

class AuditEvent(models.Model):
    """Immutable audit trail of successful sensitive actions (PHC-BR-09)."""

    entity_type = models.CharField(max_length=40)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_audit_event"
        ordering = ["at", "id"]
        indexes = [models.Index(fields=["entity_type", "entity_id", "at"], name="phc_audit_entity_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Audit events are immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit events are immutable")

    def __str__(self) -> str:
        return f"{self.entity_type}#{self.entity_id} {self.action}"


class Notification(models.Model):
    """In-app notification to one user (PHC-BR-07, PHC-BR-11, PHC-BR-13)."""

    recipient_user_id = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=40)
    message = models.CharField(max_length=300)
    entity_type = models.CharField(max_length=40, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_notification"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"to u{self.recipient_user_id}: {self.kind}"
