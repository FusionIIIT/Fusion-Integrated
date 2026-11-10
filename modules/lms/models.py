from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel


class Course(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    academic_year = models.PositiveSmallIntegerField(default=2026)
    semester = models.CharField(
        max_length=16,
        choices=[("autumn", "Autumn"), ("spring", "Spring"), ("summer", "Summer")],
        default="autumn",
    )
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)
    allow_ta_announcements = models.BooleanField(
        default=True,
        help_text="Whether TAs are permitted to post announcements for this course (BR-LMS-007).",
    )
    allow_ta_grading = models.BooleanField(
        default=True,
        help_text="Whether TAs are permitted to grade submissions for this course (BR-LMS-015).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lms_course"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class CourseMembership(TimeStampedModel):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("ta", "Teaching Assistant"),
        ("observer", "Observer"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="memberships")
    user_id = models.IntegerField(db_index=True)  # Plain integer, UserScoped, no cross-module FK
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, db_index=True)
    is_primary_instructor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lms_course_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "user_id", "role"], name="unique_lms_course_user_role"
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "role"], name="lms_cm_user_role_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} as {self.role} in {self.course.code}"


class CourseMaterial(TimeStampedModel):
    TYPE_CHOICES = [
        ("file", "File"),
        ("link", "Link"),
        ("note", "Note"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    material_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    section = models.CharField(
        max_length=100,
        default="General",
        help_text="Module or weekly section designation (e.g. Week 1, Module 2).",
    )
    content = models.TextField(blank=True, help_text="Text content for notes or description.")
    link_url = models.URLField(max_length=500, blank=True)
    file_attachment = models.FileField(upload_to="lms/materials/", blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="published")
    release_date = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_course_material"
        ordering = ["section", "created_at"]

    def is_available(self) -> bool:
        """BR-LMS-005, BR-LMS-006: Available if published and release_date passed."""
        if self.status != "published":
            return False
        if self.release_date and self.release_date > timezone.now():
            return False
        return True

    def __str__(self) -> str:
        return f"{self.title} ({self.material_type}) - {self.course.code}"


class CourseAnnouncement(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=200)
    content = models.TextField()
    posted_by_user_id = models.IntegerField(db_index=True)
    posted_by_role = models.CharField(max_length=16)
    posted_by_name = models.CharField(max_length=150, blank=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        db_table = "lms_course_announcement"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self) -> str:
        return f"[{self.course.code}] {self.title}"


class Assignment(TimeStampedModel):
    SUBMISSION_TYPE_CHOICES = [
        ("file", "File"),
        ("text", "Text"),
        ("link", "Link"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    submission_type = models.CharField(max_length=16, choices=SUBMISSION_TYPE_CHOICES)
    points_possible = models.DecimalField(max_digits=6, decimal_places=2, default=100.00)
    due_date = models.DateTimeField()
    release_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    allow_late_submissions = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_assignment"
        ordering = ["-due_date"]

    def is_available_to_students(self) -> bool:
        """BR-LMS-010, BR-LMS-011: Available to students if published and release condition met."""
        if self.status != "published":
            return False
        if self.release_date and self.release_date > timezone.now():
            return False
        return True

    def __str__(self) -> str:
        return f"{self.title} - {self.course.code}"


class AssignmentSubmission(TimeStampedModel):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("late", "Late"),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student_user_id = models.IntegerField(db_index=True)
    submission_type = models.CharField(max_length=16)
    text_response = models.TextField(blank=True)
    link_url = models.URLField(max_length=500, blank=True)
    file_submission = models.FileField(upload_to="lms/submissions/", blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="submitted")
    version = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "lms_assignment_submission"
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"Submission by User {self.student_user_id} for {self.assignment.title}"


class SubmissionGrade(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("released", "Released"),
    ]

    submission = models.OneToOneField(
        AssignmentSubmission, on_delete=models.CASCADE, related_name="grade"
    )
    points_awarded = models.DecimalField(max_digits=6, decimal_places=2)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft", db_index=True)
    graded_by_user_id = models.IntegerField()
    graded_by_role = models.CharField(max_length=16)
    graded_by_name = models.CharField(max_length=150, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "lms_submission_grade"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Grade ({self.status}): {self.points_awarded} pts for Submission {self.submission_id}"


class GradeChangeAudit(TimeStampedModel):
    grade = models.ForeignKey(SubmissionGrade, on_delete=models.CASCADE, related_name="audit_logs")
    previous_points = models.DecimalField(max_digits=6, decimal_places=2)
    new_points = models.DecimalField(max_digits=6, decimal_places=2)
    previous_feedback = models.TextField(blank=True)
    new_feedback = models.TextField(blank=True)
    changed_by_user_id = models.IntegerField()
    changed_by_name = models.CharField(max_length=150, blank=True)
    change_reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_grade_change_audit"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"Grade change on {self.grade_id} by User {self.changed_by_user_id} at {self.changed_at}"
