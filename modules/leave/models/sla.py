"""SLA rules and task tracking clocks."""

from django.db import models


class SlaRule(models.Model):
    policy = models.ForeignKey("Policy", on_delete=models.CASCADE, related_name="sla_rules")
    state = models.CharField(max_length=32)
    remind_after_hours = models.IntegerField(default=48)
    escalate_after_hours = models.IntegerField(default=96)
    escalate_to_designation = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "leave_sla_rule"

    def __str__(self) -> str:
        return f"SlaRule {self.state} remind={self.remind_after_hours}h"


class SlaClock(models.Model):
    request = models.OneToOneField(
        "LeaveRequest", on_delete=models.CASCADE, related_name="sla_clock"
    )
    state = models.CharField(max_length=32)
    entered_at = models.DateTimeField(auto_now_add=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_sla_clock"

    def __str__(self) -> str:
        return f"SlaClock req#{self.request_id} ({self.state})"
