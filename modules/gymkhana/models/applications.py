from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class MembershipApplication(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
        related_name="membership_applications",
    )
    student_id = models.PositiveBigIntegerField()
    achievements = models.TextField(blank=True)
    statement = models.TextField(blank=True)

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    reviewed_by = models.PositiveBigIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "gymkhana_membership_application"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "student_id"],
                name="gymkhana_unique_student_club_application",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["open", "approved", "rejected"]),
                name="gymkhana_valid_application_status",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "status"]),
            models.Index(fields=["student_id", "status"]),
        ]

    def __str__(self):
        return f"{self.student_id} -> {self.club_id} ({self.status})"
