from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalanceEntry(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3)
    year = models.IntegerField()
    days_delta = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(blank=True, null=True)
    request = models.ForeignKey("LeaveRequest", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Leave Balance Entry"
        verbose_name_plural = "Leave Balance Entries"
