from django.db import models
from django.core.exceptions import ValidationError

from core.db.mixins import TimeStampedModel
from modules.lms.domain.constants import ScheduleStatus, ACTIVE_SCHEDULE_STATUSES

class ScheduledRelease(TimeStampedModel):
    material = models.ForeignKey(
        'lms.CourseMaterial',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='scheduled_releases'
    )
    assignment = models.ForeignKey(
        'lms.Assignment',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='scheduled_releases'
    )
    scheduled_date = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=ScheduleStatus.CHOICES, default=ScheduleStatus.PENDING)
    error_message = models.TextField(blank=True, default='')

    def __str__(self):
        return f"ScheduledRelease for {self.material if self.material else self.assignment} - Status: {self.status}"

    class Meta:
        db_table = 'lms_scheduled_release'
        ordering = ['scheduled_date', 'id']
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(material__isnull=False) & models.Q(assignment__isnull=True))
                    | (models.Q(material__isnull=True) & models.Q(assignment__isnull=False))
                ),
                name='scheduled_release_exactly_one_target',
            ),
            models.UniqueConstraint(
                fields=['material'],
                condition=models.Q(material__isnull=False, status__in=ACTIVE_SCHEDULE_STATUSES),
                name='unique_active_scheduled_material',
            ),
            models.UniqueConstraint(
                fields=['assignment'],
                condition=models.Q(assignment__isnull=False, status__in=ACTIVE_SCHEDULE_STATUSES),
                name='unique_active_scheduled_assignment',
            )
        ]
