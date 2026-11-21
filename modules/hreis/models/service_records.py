"""Official HR service-record snapshots and append-only revisions."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class EmployeeServiceRecord(TimeStampedModel, UserScopedModel):
    appointment_details = models.JSONField(default=dict)
    department = models.CharField(max_length=120)
    designation_snapshot = models.CharField(max_length=150)
    service_history = models.JSONField(default=list)
    retirement_status = models.CharField(max_length=100, blank=True)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "hreis_service_record"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="hr_service_user_unique"),
        ]
        indexes = [models.Index(fields=["department", "user_id"], name="hr_service_dept_idx")]


class ServiceRecordRevision(models.Model):
    record = models.ForeignKey(
        EmployeeServiceRecord, on_delete=models.PROTECT, related_name="revisions"
    )
    revision_number = models.PositiveIntegerField()
    snapshot = models.JSONField()
    actor_user_id = models.IntegerField()
    actor_designation = models.CharField(max_length=150)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_service_revision"
        constraints = [
            models.UniqueConstraint(
                fields=["record", "revision_number"], name="hr_revision_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["record", "recorded_at"], name="hr_revision_history_idx"),
        ]

    def __str__(self) -> str:
        return f"Service revision {self.revision_number} for {self.record_id}"
