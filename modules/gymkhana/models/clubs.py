from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Club(TimeStampedModel):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gymkhana_club"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClubCoordinatorAssignment(TimeStampedModel):
    class Role(models.TextChoices):
        HEAD = "head", "Club Head"
        CO_COORDINATOR = "co_coordinator", "Co-Coordinator"

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="coordinator_assignments",
    )
    user_id = models.PositiveBigIntegerField()
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gymkhana_coordinator_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["club", "user_id"],
                name="gymkhana_unique_club_coordinator",
            ),
            models.CheckConstraint(
                condition=Q(role__in=["head", "co_coordinator"]),
                name="gymkhana_valid_coordinator_role",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "is_active"]),
            models.Index(fields=["club", "is_active"]),
        ]

    def __str__(self):
        return f"{self.club_id}:{self.user_id}:{self.role}"
