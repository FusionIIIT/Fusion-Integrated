from django.db import models

from core.db.mixins import TimeStampedModel


class AuditObservationStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESPONDED = "responded", "Responded"
    CLOSED = "closed", "Closed"


class AuditObservation(TimeStampedModel):
    auditor_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=64, db_index=True)
    reference_type = models.CharField(max_length=32, blank=True)
    reference_id = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=AuditObservationStatus.choices,
        default=AuditObservationStatus.OPEN,
        db_index=True,
    )
    response_text = models.TextField(blank=True)
    responded_by_id = models.IntegerField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    closure_remarks = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AuditObservation #{self.pk}: {self.title}"


class AuditLogEntry(models.Model):
    user_id = models.IntegerField(db_index=True)
    acting_role = models.CharField(max_length=64)
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=32, db_index=True)
    target_id = models.IntegerField(db_index=True)
    resulting_status = models.CharField(max_length=32, blank=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AuditLog {self.action} on {self.target_type}:{self.target_id}"
