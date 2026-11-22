from django.db import models


class FileAuditLog(models.Model):
    file_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=64, db_index=True)
    actor_user_id = models.IntegerField(db_index=True)
    actor_username = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "fts_audit_log"
        indexes = [
            models.Index(fields=["file_id", "timestamp"], name="fts_aud_file_time_idx"),
            models.Index(fields=["actor_user_id", "timestamp"], name="fts_aud_actor_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Audit {self.action} on file #{self.file_id} by {self.actor_username}"


class NotificationEvent(models.Model):
    event_type = models.CharField(max_length=64, db_index=True)
    recipient_user_id = models.IntegerField(db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    delivered = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "fts_notification_event"
        indexes = [
            models.Index(fields=["delivered", "created_at"], name="fts_notif_pending_idx"),
        ]

    def __str__(self) -> str:
        return f"Notification {self.event_type} for user {self.recipient_user_id}"
