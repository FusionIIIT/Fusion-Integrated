from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class Club(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("Technical", "Technical"),
        ("Sports", "Sports"),
        ("Cultural", "Cultural"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("confirmed", "Confirmed"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    coordinator_id = models.BigIntegerField()
    co_coordinator_id = models.BigIntegerField()
    faculty_councillor_id = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    class Meta:
        db_table = "gymkhana_club"
        indexes = [
            models.Index(fields=["status"], name="gymkhana_club_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="gymkhana_club_name_uniq"),
            models.CheckConstraint(
                condition=~Q(coordinator_id=F("co_coordinator_id")),
                name="gymkhana_club_distinct_coordinators",
            ),
            models.CheckConstraint(
                condition=Q(category__in=["Technical", "Sports", "Cultural"]),
                name="gymkhana_club_category_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["open", "confirmed"]),
                name="gymkhana_club_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ClubLeadershipHistory(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="leadership_history",
    )
    coordinator_id = models.BigIntegerField()
    co_coordinator_id = models.BigIntegerField()
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    changed_by_user_id = models.BigIntegerField()

    class Meta:
        db_table = "gymkhana_club_leadership_history"
        indexes = [
            models.Index(fields=["club", "effective_to"], name="gymkhana_lead_hist_idx"),
        ]

    def __str__(self) -> str:
        to_str = self.effective_to or "present"
        return f"{self.club.name} leadership ({self.effective_from} - {to_str})"
