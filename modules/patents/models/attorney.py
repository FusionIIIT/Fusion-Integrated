from django.db import models

from core.db.mixins import TimeStampedModel


class AttorneyPanelMember(TimeStampedModel):
    user_id = models.IntegerField(unique=True, db_index=True)
    firm_name = models.CharField(max_length=255)
    expertise_domains = models.JSONField(default=list)
    active_workload = models.PositiveIntegerField(default=0)
    is_approved_panel = models.BooleanField(default=True)

    class Meta:
        db_table = "patents_attorney_panel"
