from django.db import models

from core.db.mixins import TimeStampedModel

from .base import AppendOnly


class CourseWorkspace(TimeStampedModel):
    external_offering_key = models.CharField(max_length=68, unique=True)
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)
    details_published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField(null=True)


class CoursePolicyVersion(AppendOnly):
    workspace = models.ForeignKey("lms.CourseWorkspace", on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    effective_from = models.DateTimeField()
    can_ta_post_announcements = models.BooleanField(default=False)
    decision_version = models.CharField(max_length=32, default="A9-LMS-BP-0.2")
    author_user_id = models.IntegerField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "version"), name="lms_policy_version_uniq"
            ),
            models.UniqueConstraint(
                fields=("workspace", "effective_from"), name="lms_policy_time_uniq"
            ),
        ]

    def __str__(self):
        return f"Course policy {self.workspace_id}:{self.version}"
