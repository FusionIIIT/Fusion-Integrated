"""Club aggregate models for Gymkhana."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, F, Q

from modules.gymkhana.domain.constants import (
    ALLOWED_CLUB_CATEGORIES,
    CLUB_STATUS_OPEN,
    CLUB_STATUSES,
)


class Club(models.Model):
    """Gymkhana student club entity."""

    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    coordinator_id = models.IntegerField()
    co_coordinator_id = models.IntegerField()
    faculty_councillor_id = models.IntegerField()
    status = models.CharField(max_length=20, default=CLUB_STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gymkhana_club"
        ordering = ["name"]
        constraints = [
            CheckConstraint(
                condition=Q(category__in=ALLOWED_CLUB_CATEGORIES),
                name="check_gymkhana_club_category",
            ),
            CheckConstraint(
                condition=Q(status__in=CLUB_STATUSES),
                name="check_gymkhana_club_status",
            ),
            CheckConstraint(
                condition=~Q(coordinator_id=F("co_coordinator_id")),
                name="check_distinct_coordinator_co_coordinator",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


class ClubLeadershipHistory(models.Model):
    """Audit log of club leadership changes (BR-GYM-016)."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="leadership_history")
    coordinator_id = models.IntegerField()
    co_coordinator_id = models.IntegerField()
    changed_by_id = models.IntegerField()
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_club_leadership_history"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"LeadershipHistory(club_id={self.club_id}, at={self.changed_at})"
