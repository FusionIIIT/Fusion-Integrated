from django.db import models

class AuditLog(models.Model):
    module = models.CharField(max_length=30, default="hr_eis", db_index=True)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=50, db_index=True)
    actor = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    from_state = models.CharField(max_length=50, blank=True, default="")
    to_state = models.CharField(max_length=50, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.TextField(blank=True, default="")

    def __str__(self):
        return f"[{self.timestamp}] {self.actor} -> {self.action} on {self.entity_type}#{self.entity_id}"

class NotificationRecord(models.Model):
    recipient = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=150)
    message = models.TextField()
    category = models.CharField(max_length=50, default="Event")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification to {self.recipient}: {self.title}"

class WorkflowSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    updated_by = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key} = {self.value}"
