from django.db import models
from core.db.mixins import TimeStampedModel


class WorkflowTask(TimeStampedModel):
    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    assigned_user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=64)
    task_type = models.CharField(max_length=32)  # substitute, unit_head, higher_sanction
    status = models.CharField(max_length=16, default="pending")
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        indexes = [
            models.Index(fields=["assigned_user_id", "status"], name="elm_task_user_status_idx"),
        ]
