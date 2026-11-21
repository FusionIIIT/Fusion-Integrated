from django.db import models


class CaseEvent(models.Model):
    case_type = models.CharField(max_length=20)
    case_id = models.IntegerField()
    from_state = models.CharField(max_length=80, blank=True)
    to_state = models.CharField(max_length=80, blank=True)
    action = models.CharField(max_length=40)
    actor_id = models.IntegerField()
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["case_type", "case_id"])]

    def __str__(self):
        return f"{self.case_type} #{self.case_id}: {self.action}"


class Notification(models.Model):
    recipient_id = models.IntegerField(db_index=True)
    channel = models.CharField(
        max_length=10, choices=[("alert", "alert"), ("email", "email")]
    )
    message = models.TextField()
    case_type = models.CharField(max_length=20)
    case_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.channel} to {self.recipient_id} ({self.case_type} #{self.case_id})"
