from django.db import models

from core.db.mixins import TimeStampedModel


class DecisionType(models.TextChoices):
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    ESCALATE = "escalate", "Escalate"


class ApprovalAction(TimeStampedModel):
    content_type = models.CharField(
        max_length=32, choices=[("request", "Request"), ("travel", "Travel")]
    )
    object_id = models.IntegerField(db_index=True)
    actor_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=64)
    decision = models.CharField(max_length=32, choices=DecisionType.choices)
    remarks = models.TextField()
    level = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-created_at"]


class ClarificationQuery(TimeStampedModel):
    content_type = models.CharField(
        max_length=32, choices=[("request", "Request"), ("travel", "Travel")]
    )
    object_id = models.IntegerField(db_index=True)
    sender_id = models.IntegerField(db_index=True)
    sender_role = models.CharField(max_length=64, default="finance_staff")
    query_text = models.TextField()
    response_text = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=[("pending", "Pending"), ("responded", "Responded")],
        default="pending",
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
