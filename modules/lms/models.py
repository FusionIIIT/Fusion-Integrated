"""LMS-owned course workspace and learning content."""
from __future__ import annotations

from uuid import uuid4

from django.core.files.storage import FileSystemStorage
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel

_lms_storage = FileSystemStorage()


def _upload_key(_instance, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower()[:12] if "." in filename else "bin"
    return f"{uuid4().hex}.{suffix}"


class CourseWorkspace(TimeStampedModel):
    """LMS presentation data keyed by the authoritative external course id."""

    source_course_id = models.CharField(max_length=120, unique=True)
    course_code = models.CharField(max_length=64)
    title = models.CharField(max_length=200)
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)

    class Meta:
        db_table = "lms_course_workspace"
        indexes = [models.Index(fields=["course_code"], name="lms_course_code_idx")]

    def __str__(self) -> str:
        return f"{self.course_code} — {self.title}"


class CourseSection(TimeStampedModel):
    KIND = [("module", "Module"), ("week", "Week")]

    course = models.ForeignKey(CourseWorkspace, on_delete=models.CASCADE,
                               related_name="sections")
    kind = models.CharField(max_length=8, choices=KIND)
    title = models.CharField(max_length=160)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "lms_course_section"
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["course", "sort_order"],
                                name="lms_section_order_idx")]


class CourseMaterial(TimeStampedModel):
    KIND = [("file", "File"), ("link", "Link"), ("note", "Note")]
    STATUS = [("draft", "Draft"), ("scheduled", "Scheduled"),
              ("published", "Published")]

    course = models.ForeignKey(CourseWorkspace, on_delete=models.CASCADE,
                               related_name="materials")
    section = models.ForeignKey(CourseSection, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="materials")
    kind = models.CharField(max_length=8, choices=KIND)
    title = models.CharField(max_length=200)
    note = models.TextField(blank=True)
    link = models.URLField(max_length=500, blank=True)
    file = models.FileField(storage=_lms_storage, upload_to=_upload_key,
                            blank=True, max_length=255)
    release_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    created_by_user_id = models.IntegerField()
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lms_course_material"
        indexes = [
            models.Index(fields=["course", "status", "release_at"],
                         name="lms_material_release_idx"),
            models.Index(fields=["section", "created_at"],
                         name="lms_material_section_idx"),
        ]


class CourseAnnouncement(TimeStampedModel):
    course = models.ForeignKey(CourseWorkspace, on_delete=models.CASCADE,
                               related_name="announcements")
    title = models.CharField(max_length=200)
    content = models.TextField()
    posted_by_user_id = models.IntegerField()
    published_at = models.DateTimeField()

    class Meta:
        db_table = "lms_course_announcement"
        indexes = [models.Index(fields=["course", "-published_at"],
                                name="lms_announce_recent_idx")]


class Assignment(TimeStampedModel):
    SUBMISSION_TYPES = [("file", "File"), ("text", "Text"), ("link", "Link")]
    STATUS = [("draft", "Draft"), ("scheduled", "Scheduled"),
              ("available", "Available")]

    course = models.ForeignKey(CourseWorkspace, on_delete=models.CASCADE,
                               related_name="assignments")
    title = models.CharField(max_length=200)
    due_at = models.DateTimeField()
    instructions = models.TextField()
    submission_type = models.CharField(max_length=8, choices=SUBMISSION_TYPES)
    points_possible = models.DecimalField(max_digits=8, decimal_places=2)
    file = models.FileField(storage=_lms_storage, upload_to=_upload_key,
                            blank=True, max_length=255)
    release_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    created_by_user_id = models.IntegerField()
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lms_assignment"
        indexes = [
            models.Index(fields=["course", "status", "release_at"],
                         name="lms_assignment_release_idx"),
            models.Index(fields=["course", "due_at"], name="lms_assignment_due_idx"),
        ]


class AssignmentSubmission(TimeStampedModel, UserScopedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT,
                                   related_name="submissions")
    content_type = models.CharField(max_length=8, choices=Assignment.SUBMISSION_TYPES)
    text = models.TextField(blank=True)
    link = models.URLField(max_length=500, blank=True)
    file = models.FileField(storage=_lms_storage, upload_to=_upload_key,
                            blank=True, max_length=255)
    submitted_at = models.DateTimeField()

    class Meta:
        db_table = "lms_assignment_submission"
        indexes = [
            models.Index(fields=["assignment", "user_id", "-submitted_at"],
                         name="lms_submission_owner_idx"),
        ]


class SubmissionGrade(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("released", "Released")]

    submission = models.OneToOneField(AssignmentSubmission, on_delete=models.CASCADE,
                                      related_name="grade")
    points = models.DecimalField(max_digits=8, decimal_places=2)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=8, choices=STATUS, default="draft")
    graded_by_user_id = models.IntegerField()
    graded_at = models.DateTimeField()
    released_by_user_id = models.IntegerField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lms_submission_grade"


class ReleasedGradeChange(TimeStampedModel):
    """Audit record required whenever already-released points/feedback change."""

    grade = models.ForeignKey(SubmissionGrade, on_delete=models.CASCADE,
                              related_name="released_changes")
    old_points = models.DecimalField(max_digits=8, decimal_places=2)
    new_points = models.DecimalField(max_digits=8, decimal_places=2)
    old_feedback = models.TextField(blank=True)
    new_feedback = models.TextField(blank=True)
    changed_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_released_grade_change"
        indexes = [models.Index(fields=["grade", "created_at"],
                                name="lms_grade_change_idx")]
