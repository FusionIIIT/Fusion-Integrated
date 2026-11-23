from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Assignment(TimeStampedModel):
    workspace = models.ForeignKey("lms.CourseWorkspace", on_delete=models.PROTECT)
    title = models.CharField(max_length=200, blank=True)
    instructions = models.TextField()
    due_at = models.DateTimeField()
    submission_type = models.CharField(max_length=4)
    points_possible = models.DecimalField(max_digits=10, decimal_places=2)
    state = models.CharField(max_length=10, default="DRAFT")
    release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    author_user_id = models.IntegerField()
    publisher_user_id = models.IntegerField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(points_possible__gte=0), name="lms_assignment_points"
            ),
            models.CheckConstraint(
                condition=Q(submission_type__in=("FILE", "TEXT", "LINK")),
                name="lms_assignment_kind_valid",
            ),
            models.CheckConstraint(
                condition=Q(state__in=("DRAFT", "SCHEDULED", "AVAILABLE")),
                name="lms_assignment_state_valid",
            ),
            models.CheckConstraint(
                condition=~Q(state="SCHEDULED") | Q(release_at__isnull=False),
                name="lms_assignment_scheduled_time",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "state"), name="lms_assignment_scope"),
            models.Index(fields=("state", "release_at"), name="lms_assignment_due"),
        ]
