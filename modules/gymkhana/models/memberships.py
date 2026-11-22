"""Membership applications (BW-GYM-01)."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models.clubs import Club


class Membership(TimeStampedModel):
    STATUS_CHOICES = [(sm.OPEN, "Open"), (sm.CONFIRMED, "Confirmed")]

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="memberships")
    user_id = models.IntegerField()
    description = models.TextField(max_length=4000)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=sm.OPEN)
    remarks = models.TextField(max_length=1000, blank=True)
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_membership"
        constraints = [
            # BR-GYM-009; keyed on the pair, so other clubs stay open (BR-GYM-008).
            models.UniqueConstraint(fields=["club", "user_id"],
                                    name="gym_membership_one_per_club"),
            models.CheckConstraint(condition=Q(status__in=sm.STATES),
                                   name="gym_membership_status_valid"),
        ]
        indexes = [
            models.Index(fields=["club", "status", "created_at"],
                         name="gym_membership_club_status_idx"),
            models.Index(fields=["user_id", "created_at"],
                         name="gym_membership_user_idx"),
        ]
