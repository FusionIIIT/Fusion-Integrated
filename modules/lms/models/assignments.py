"""Course assignment model."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from modules.lms.domain.constants import AssignmentStatus, SubmissionType


class Assignment(models.Model):
    STATUS_CHOICES = [(s, s) for s in AssignmentStatus.ALL]
    TYPE_CHOICES = [(t, t) for t in SubmissionType.ALL]

    course_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    instructions = models.TextField()
    points_possible = models.DecimalField(max_digits=6, decimal_places=2)
    submission_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    due_date = models.DateTimeField()
    release_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=AssignmentStatus.DRAFT)
    created_by = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_assignment"
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"
        indexes = [
            models.Index(fields=["course_id", "status", "release_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(points_possible__gt=0),
                name="lms_assignment_points_positive",
            ),
            models.CheckConstraint(
                condition=Q(release_date__isnull=True) | Q(due_date__gte=F("release_date")),
                name="lms_assignment_due_after_release",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} (Course {self.course_id})"
