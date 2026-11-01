"""Graduate Seminar models for BW-OAP-09."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class SeminarSchedulingRequest(TimeStampedModel):
    """PG student's graduate seminar scheduling request (OA-UC-51)."""
    STATUS_CHOICES = [
        ("AWAITING_SCHEDULING", "Awaiting Scheduling"),
        ("SCHEDULED", "Scheduled"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    student_id = models.IntegerField(db_index=True)
    student_name = models.CharField(max_length=150)
    programme = models.CharField(max_length=60, default="M.Tech")
    department = models.CharField(max_length=80, blank=True)
    topic = models.CharField(max_length=255)
    abstract = models.TextField()
    preferred_date = models.DateField(null=True, blank=True)
    faculty_advisor_id = models.IntegerField(null=True, blank=True)
    faculty_advisor_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="AWAITING_SCHEDULING",
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "department_seminar_request"
        indexes = [
            models.Index(fields=["student_id", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Request #{self.pk} - {self.student_name}: {self.topic[:40]} [{self.status}]"


class GraduateSeminar(TimeStampedModel):
    """Scheduled graduate seminar record (OA-UC-53, OA-BR-62)."""
    request = models.OneToOneField(
        SeminarSchedulingRequest,
        on_delete=models.CASCADE,
        related_name="seminar",
    )
    title = models.CharField(max_length=255)
    speaker_id = models.IntegerField(db_index=True)
    speaker_name = models.CharField(max_length=150)
    scheduled_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=100)
    session_chair = models.CharField(max_length=150, blank=True)
    remarks = models.TextField(blank=True)
    scheduled_by_id = models.IntegerField()
    scheduled_by_name = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = "department_graduate_seminar"
        indexes = [
            models.Index(fields=["scheduled_date", "start_time"]),
            models.Index(fields=["speaker_id"]),
        ]

    def __str__(self) -> str:
        return f"Seminar: {self.title[:40]} on {self.scheduled_date} at {self.venue}"


class SeminarSchedulingHistory(TimeStampedModel):
    """Audit log of seminar scheduling actions (OA-BR-62, AFR-OAP-048)."""
    seminar = models.ForeignKey(
        GraduateSeminar,
        on_delete=models.CASCADE,
        related_name="history_logs",
    )
    action = models.CharField(max_length=50)
    details = models.TextField()
    recorded_by_id = models.IntegerField()
    recorded_by_name = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = "department_seminar_history"
        indexes = [
            models.Index(fields=["seminar", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"History #{self.pk} for Seminar #{self.seminar_id}: {self.action}"
