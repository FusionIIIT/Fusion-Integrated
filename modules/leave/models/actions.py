from django.db import models
from core.db.mixins import TimeStampedModel

class LeaveActionHistory(TimeStampedModel):
    application = models.ForeignKey("leave.LeaveApplication", on_delete=models.CASCADE, related_name="action_history")
    actor_user_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=50)  # employee, substitute, unit_head, establishment, director, leave_admin
    action = models.CharField(max_length=50)  # applied, substitute_accepted, substitute_declined, unit_head_recommended, unit_head_approved, approved, rejected, withdrawn, cancel_requested, cancelled, extension_requested, resumption_submitted, record_maintained
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "leave_action_history"
        ordering = ["created_at"]