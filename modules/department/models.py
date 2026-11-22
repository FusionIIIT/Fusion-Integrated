from django.contrib.postgres.fields import ArrayField
from django.db import models


class Announcement(models.Model):
    department = models.CharField(max_length=200)
    content = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    target_roles = ArrayField(models.CharField(max_length=80), default=list, blank=True)
    target_programmes = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    target_batch_years = ArrayField(models.PositiveSmallIntegerField(), default=list, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(department=""), name="dept_announcement_has_scope",
            ),
            models.CheckConstraint(
                condition=~models.Q(content=""), name="dept_announcement_has_content",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "-id"], condition=models.Q(is_active=True),
                         name="dept_announcement_active_idx"),
        ]

    def __str__(self):
        return f"Announcement {self.pk} ({self.department})"
