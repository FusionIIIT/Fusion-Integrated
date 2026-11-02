from django.db import models

from core.db.mixins import TimeStampedModel


class ArchivalRequest(TimeStampedModel):
    CLASSIFICATIONS = [
        ("critical", "Critical"),
        ("sensitive", "Sensitive"),
        ("routine", "Routine"),
        ("archival", "Archival"),
    ]
    STATUSES = [
        ("submitted", "Submitted"),
        ("hod_approved", "HoD approved"),
        ("rejected", "Rejected"),
    ]

    requester_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=80, db_index=True)
    file_name = models.CharField(max_length=180)
    file_date = models.DateField()
    owners = models.JSONField(default=list)
    file_type = models.CharField(max_length=80)
    reason = models.TextField()
    attachment_url = models.URLField(max_length=500)
    initial_classification = models.CharField(
        max_length=16, choices=CLASSIFICATIONS, default="routine")
    status = models.CharField(max_length=16, choices=STATUSES, default="submitted")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["department", "status"]),
            models.Index(fields=["requester_user_id", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.status})"
