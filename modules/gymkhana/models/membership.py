"""Club membership application and enrollment models for Gymkhana."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from modules.gymkhana.domain.constants import (
    MEMBERSHIP_STATUS_OPEN,
    MEMBERSHIP_STATUSES,
)
from modules.gymkhana.models.club import Club


class ClubMembership(models.Model):
    """Student membership application and confirmed enrollment."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="memberships")
    student_id = models.IntegerField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default=MEMBERSHIP_STATUS_OPEN)
    remarks = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_club_membership"
        ordering = ["-applied_at"]
        constraints = [
            UniqueConstraint(
                fields=["club", "student_id"],
                name="unique_club_membership_per_student",
            ),
            CheckConstraint(
                condition=Q(status__in=MEMBERSHIP_STATUSES),
                name="check_gymkhana_membership_status",
            ),
        ]

    def __str__(self) -> str:
        return f"Membership(club={self.club.name}, student={self.student_id}, status={self.status})"
