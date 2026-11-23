from django.db import models
from django.db.models import CheckConstraint, Index, Q, UniqueConstraint

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain.constants import MEMBERSHIP_STATUSES, STATUS_OPEN
from modules.gymkhana.models.club import Club


class ClubMembership(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="memberships")
    student_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, default=STATUS_OPEN)
    remarks = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_membership"
        indexes = [
            Index(fields=["club", "status"], name="gym_mem_club_status_idx"),
            Index(fields=["student_id", "status"], name="gym_mem_stud_status_idx"),
        ]
        constraints = [
            UniqueConstraint(
                fields=["club", "student_id"],
                name="gymkhana_unique_student_club_membership",
            ),
            CheckConstraint(
                condition=Q(status__in=list(MEMBERSHIP_STATUSES)),
                name="gymkhana_membership_valid_status",
            ),
        ]
