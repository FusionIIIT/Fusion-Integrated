from django.db import models
from django.db.models import CheckConstraint, Index, Q, UniqueConstraint

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain.constants import (
    CLUB_CATEGORIES,
    CLUB_STATUSES,
    LEADERSHIP_ROLES,
    STATUS_OPEN,
)


class Club(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    faculty_councillor_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, default=STATUS_OPEN)

    class Meta:
        db_table = "gymkhana_club"
        indexes = [
            Index(fields=["status", "category"], name="gym_club_status_cat_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(category__in=list(CLUB_CATEGORIES)),
                name="gymkhana_club_valid_category",
            ),
            CheckConstraint(
                condition=Q(status__in=list(CLUB_STATUSES)),
                name="gymkhana_club_valid_status",
            ),
        ]


class ClubLeadership(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="leaderships")
    student_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=30)
    is_current = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "gymkhana_leadership"
        indexes = [
            Index(fields=["club", "is_current"], name="gym_lead_club_curr_idx"),
            Index(fields=["student_id", "is_current"], name="gym_lead_stud_curr_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(role__in=list(LEADERSHIP_ROLES)),
                name="gymkhana_lead_valid_role",
            ),
            UniqueConstraint(
                fields=["club", "role"],
                condition=Q(is_current=True),
                name="gymkhana_unique_current_club_role",
            ),
        ]
