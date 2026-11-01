from django.db import models

from core.db.mixins import TimeStampedModel


class Announcement(TimeStampedModel):
    """Represents a departmental announcement."""
    department = models.ForeignKey("department.Department", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    body = models.TextField()
    target_roles = models.JSONField(default=list)
    target_programme = models.CharField(max_length=100, blank=True, null=True)
    target_batch_year = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('active', 'Active'),
            ('hidden', 'Hidden'),
            ('deleted', 'Deleted'),
        ],
        default='active',
    )
    published_by_user_id = models.IntegerField()
    published_role = models.CharField(max_length=50)

    class Meta:
        db_table = 'department_announcement'
        indexes = [
            models.Index(fields=['department', 'status'], name='dept_announcement_dept_status'),
        ]

    def __str__(self):
        return self.title
