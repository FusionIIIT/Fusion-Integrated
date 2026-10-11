"""SLA-controlled actionable workflow tasks (BR-EL-032, BR-EL-033, WF-EL-08)."""
from django.db import models

from core.db.mixins import TimeStampedModel


class WorkflowTask(TimeStampedModel):
    KINDS = (("substitute", "Substitute consent"),
             ("unit_head", "Unit Head review"),
             ("establishment", "Establishment routing"),
             ("final_sanction", "Final sanction"),
             ("director_self", "Director self-sanction"),
             ("cancellation", "Cancellation decision"),
             ("resumption", "Resumption verification"))
    STATUSES = (("pending", "Pending"), ("done", "Done"),
                ("superseded", "Superseded"), ("cancelled", "Cancelled"))

    application = models.ForeignKey(
        "leave.LeaveApplication", on_delete=models.CASCADE, related_name="tasks")
    kind = models.CharField(max_length=24, choices=KINDS)
    status = models.CharField(max_length=16, choices=STATUSES, default="pending",
                              db_index=True)
    assignee_user_id = models.IntegerField(null=True, blank=True)
    assignee_role = models.CharField(max_length=80, blank=True)
    sla_controlled = models.BooleanField(default=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    escalate_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_workflow_task"
        indexes = [
            models.Index(fields=["status", "reminder_at"], name="leave_task_sla"),
            models.Index(fields=["application", "status"], name="leave_task_app"),
        ]
