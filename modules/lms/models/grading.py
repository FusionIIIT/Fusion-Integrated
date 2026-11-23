from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel

from .base import AppendOnly


class Grade(TimeStampedModel):
    submission = models.OneToOneField(
        "lms.Submission", on_delete=models.PROTECT, related_name="grade"
    )
    points = models.DecimalField(max_digits=10, decimal_places=2)
    feedback = models.TextField(blank=True)
    state = models.CharField(max_length=8, default="DRAFT")
    grader_user_id = models.IntegerField()
    graded_at = models.DateTimeField()
    released_by_user_id = models.IntegerField(null=True)
    released_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(points__gte=0), name="lms_grade_points_nonnegative"),
            models.CheckConstraint(
                condition=Q(state__in=("DRAFT", "RELEASED")), name="lms_grade_state"
            ),
            models.CheckConstraint(
                condition=~Q(state="RELEASED")
                | (Q(released_at__isnull=False) & Q(released_by_user_id__isnull=False)),
                name="lms_grade_release_attribution",
            ),
        ]


class GradeAuditLog(AppendOnly):
    submission = models.ForeignKey(
        "lms.Submission", on_delete=models.PROTECT, related_name="grade_audit"
    )
    actor_user_id = models.IntegerField()
    operation = models.CharField(max_length=16)
    old_points = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    new_points = models.DecimalField(max_digits=10, decimal_places=2)
    old_feedback = models.TextField(blank=True)
    new_feedback = models.TextField(blank=True)
    old_state = models.CharField(max_length=8)
    new_state = models.CharField(max_length=8)
    changed_at = models.DateTimeField()

    def __str__(self):
        return f"Grade audit {self.pk} for submission {self.submission_id}"
