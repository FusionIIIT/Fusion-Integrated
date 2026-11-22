from django.db import models

from modules.iwd.models.complaint import Complaint
from modules.iwd.models.estimate import RepairEstimate


class DecisionAuditTrail(models.Model):
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="audit_trails"
    )
    estimate = models.ForeignKey(
        RepairEstimate, null=True, blank=True, on_delete=models.SET_NULL
    )
    actor_user_id = models.IntegerField(db_index=True)
    acting_role = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    from_state = models.CharField(max_length=50)
    to_state = models.CharField(max_length=50)
    decision_reason = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "iwd_decision_audit_trail"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.action} on {self.complaint_id} by user {self.actor_user_id}"
