"""LMS-owned records. Identity and course registrations remain in IAM."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class CourseWorkspace(TimeStampedModel):
    external_offering_key = models.CharField(max_length=68, unique=True)
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)
    details_published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField(null=True)


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError("Historical records cannot be updated")

    def delete(self):
        raise ValueError("Historical records cannot be deleted")


class AppendOnly(models.Model):
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Historical records cannot be updated")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Historical records cannot be deleted")


class CoursePolicyVersion(AppendOnly):
    workspace = models.ForeignKey(CourseWorkspace, on_delete=models.PROTECT)
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


class MaterialSection(TimeStampedModel):
    workspace = models.ForeignKey(CourseWorkspace, on_delete=models.PROTECT)
    kind = models.CharField(max_length=6, choices=[("MODULE", "Module"), ("WEEK", "Week")])
    label = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=("MODULE", "WEEK")), name="lms_section_kind_valid"
            )
        ]


class StoredFile(TimeStampedModel):
    workspace = models.ForeignKey(CourseWorkspace, on_delete=models.PROTECT)
    owner_user_id = models.IntegerField()
    storage_key = models.CharField(max_length=160, unique=True)
    name = models.CharField(max_length=200)
    mime_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)


def payload_constraint(text_kind):
    return (
        (Q(kind=text_kind, url="", stored_file__isnull=True) & ~Q(text=""))
        | (Q(kind="LINK", text="", stored_file__isnull=True) & ~Q(url=""))
        | Q(kind="FILE", text="", url="", stored_file__isnull=False)
    )


class Material(TimeStampedModel):
    workspace = models.ForeignKey(CourseWorkspace, on_delete=models.PROTECT)
    section = models.ForeignKey(MaterialSection, null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=4)
    text = models.TextField(blank=True)
    url = models.URLField(max_length=2000, blank=True)
    stored_file = models.ForeignKey(StoredFile, null=True, on_delete=models.PROTECT)
    order = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=10, default="DRAFT")
    release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    author_user_id = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=payload_constraint("NOTE"), name="lms_material_payload"
            ),
            models.CheckConstraint(
                condition=Q(state__in=("DRAFT", "SCHEDULED", "PUBLISHED")),
                name="lms_material_state_valid",
            ),
            models.CheckConstraint(
                condition=~Q(state="SCHEDULED") | Q(release_at__isnull=False),
                name="lms_material_scheduled_time",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "state", "order"), name="lms_material_scope"),
            models.Index(fields=("state", "release_at"), name="lms_material_due"),
        ]


class Announcement(TimeStampedModel):
    workspace = models.ForeignKey(CourseWorkspace, on_delete=models.PROTECT)
    content = models.TextField()
    author_user_id = models.IntegerField()


class Assignment(TimeStampedModel):
    workspace = models.ForeignKey(CourseWorkspace, on_delete=models.PROTECT)
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


class Submission(UserScopedModel, TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT)
    kind = models.CharField(max_length=4)
    text = models.TextField(blank=True)
    url = models.URLField(max_length=2000, blank=True)
    stored_file = models.ForeignKey(StoredFile, null=True, on_delete=models.PROTECT)
    submitted_at = models.DateTimeField()
    policy_version = models.CharField(max_length=32, default="A9-LMS-BP-0.2")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("assignment", "user_id"), name="lms_submission_assignment_user_uniq"
            ),
            models.CheckConstraint(
                condition=payload_constraint("TEXT"), name="lms_submission_payload"
            ),
        ]


class Grade(TimeStampedModel):
    submission = models.OneToOneField(Submission, on_delete=models.PROTECT, related_name="grade")
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
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="grade_audit")
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
