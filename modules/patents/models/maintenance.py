from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import PatentApplication


class RenewalHistory(TimeStampedModel):
    """One maintenance cycle: the Director's decision and, for a renewal, the recorded
    maintenance action and the next scheduled due date (PMS-AFR-114, PMS-AFR-115)."""

    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="renewal_history",
    )
    cycle_due_date = models.DateField(null=True, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(max_length=20)
    decided_by_user_id = models.IntegerField()
    decided_at = models.DateTimeField()
    action_reference = models.CharField(max_length=200, blank=True, default="")
    action_recorded_by_user_id = models.IntegerField(null=True, blank=True)
    action_recorded_at = models.DateTimeField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "patents_renewal_history"
        ordering = ("id",)
