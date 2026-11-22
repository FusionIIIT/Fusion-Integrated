from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.club import Club


class ClubMembership(TimeStampedModel):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("confirmed", "Confirmed"),
    ]

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    student_id = models.BigIntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    class Meta:
        db_table = "gymkhana_club_membership"
        indexes = [
            models.Index(fields=["club", "status"], name="gymkhana_member_club_stat_idx"),
            models.Index(fields=["student_id", "status"], name="gymkhana_member_stu_stat_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "student_id"],
                name="gymkhana_membership_club_student_uniq",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["open", "confirmed"]),
                name="gymkhana_membership_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.club.name} - Student {self.student_id} ({self.status})"
