"""Clubs and their leadership (BR-GYM-001…004, BR-GYM-016)."""
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain import rules
from modules.gymkhana.domain import state_machine as sm


class Club(TimeStampedModel):
    CATEGORY_CHOICES = [(rules.TECHNICAL, "Technical"), (rules.SPORTS, "Sports"),
                        (rules.CULTURAL, "Cultural")]
    STATUS_CHOICES = [(sm.OPEN, "Open"), (sm.CONFIRMED, "Confirmed")]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES)
    description = models.TextField(max_length=4000)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=sm.OPEN)
    faculty_councillor_user_id = models.IntegerField()
    created_by_user_id = models.IntegerField()
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_club"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="gym_club_name_unique_ci"),
            models.CheckConstraint(condition=Q(category__in=rules.CATEGORIES),
                                   name="gym_club_category_valid"),
            models.CheckConstraint(condition=Q(status__in=sm.STATES),
                                   name="gym_club_status_valid"),
            models.CheckConstraint(
                condition=(Q(status=sm.OPEN, approved_by_user_id__isnull=True,
                             approved_at__isnull=True)
                           | Q(status=sm.CONFIRMED, approved_by_user_id__isnull=False,
                               approved_at__isnull=False)),
                name="gym_club_confirmed_has_approver"),
        ]
        indexes = [
            models.Index(fields=["status", "name"], name="gym_club_status_name_idx"),
            models.Index(fields=["faculty_councillor_user_id"],
                         name="gym_club_councillor_idx"),
        ]

    def __str__(self) -> str:
        return self.name


LEADER_ROLES = ("coordinator", "co_coordinator")


class LeadershipAssignment(TimeStampedModel):
    COORDINATOR, CO_COORDINATOR = LEADER_ROLES
    ROLE_CHOICES = [(COORDINATOR, "Coordinator"), (CO_COORDINATOR, "Co-coordinator")]

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="leaders")
    user_id = models.IntegerField()
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_leadership_assignment"
        constraints = [
            models.UniqueConstraint(fields=["club", "role"],
                                    condition=Q(valid_to__isnull=True),
                                    name="gym_leader_one_current_per_role"),
            models.UniqueConstraint(fields=["club", "user_id"],
                                    condition=Q(valid_to__isnull=True),
                                    name="gym_leader_distinct_people"),
            models.CheckConstraint(condition=Q(role__in=LEADER_ROLES),
                                   name="gym_leader_role_valid"),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gte=models.F("valid_from")),
                name="gym_leader_valid_range"),
        ]
        indexes = [
            models.Index(fields=["user_id"], condition=Q(valid_to__isnull=True),
                         name="gym_leader_current_user_idx"),
        ]
