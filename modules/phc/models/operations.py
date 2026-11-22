from django.db import models

from core.db.mixins import TimeStampedModel
from modules.phc.models._immutable import AppendOnlyModel


class AmbulanceLog(TimeStampedModel):
    used_at = models.DateTimeField()
    patient_name = models.CharField(max_length=160)
    destination = models.CharField(max_length=300)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_ambulance_log"
        indexes = [models.Index(fields=["-used_at"], name="phc_ambulance_recent_idx")]

    def __str__(self) -> str:
        return f"Ambulance {self.used_at:%Y-%m-%d %H:%M}"


class HealthAdvisory(TimeStampedModel):
    title = models.CharField(max_length=180)
    body = models.TextField()
    published_at = models.DateTimeField()
    published_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_health_advisory"
        indexes = [models.Index(fields=["-published_at"], name="phc_advisory_recent_idx")]

    def __str__(self) -> str:
        return self.title


class AuditRecord(AppendOnlyModel):
    actor_user_id = models.IntegerField()
    resource_type = models.CharField(max_length=40)
    resource_id = models.BigIntegerField()
    action = models.CharField(max_length=40)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_audit_record"
        indexes = [
            models.Index(fields=["resource_type", "resource_id", "created_at"],
                         name="phc_audit_resource_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.resource_type}:{self.resource_id} {self.action}"


class Notification(AppendOnlyModel):
    recipient_user_id = models.IntegerField()
    kind = models.CharField(max_length=40)
    message = models.CharField(max_length=300)
    resource_type = models.CharField(max_length=40)
    resource_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_notification"
        indexes = [
            models.Index(fields=["recipient_user_id", "-created_at"],
                         name="phc_notification_inbox_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} -> {self.recipient_user_id}"
