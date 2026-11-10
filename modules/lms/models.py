"""LMS Course Workspace data models.

User ids deliberately remain plain integers: IAM owns identities and directory
facts, so course memberships must not introduce cross-module foreign keys
(ADR-0013).
"""
from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
    SubmissionType,
)


class Course(TimeStampedModel):
    """A course offering workspace in the LMS."""

    STATUS_CHOICES = [
        (CourseStatus.DRAFT, "Draft"),
        (CourseStatus.PUBLISHED, "Published"),
    ]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    syllabus = models.TextField(blank=True)
    schedule = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=CourseStatus.PUBLISHED)

    class Meta:
        db_table = "lms_course"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


class CourseMembership(TimeStampedModel):
    """Membership of an authenticated user in a course workspace.

    Governs access and role-dependent capabilities (Faculty, TA, Student, Observer)
    in compliance with BR-LMS-001, BR-LMS-002, BR-LMS-003, and BR-LMS-004.
    """

    ROLE_CHOICES = [
        (CourseRole.FACULTY, "Faculty"),
        (CourseRole.STUDENT, "Student"),
        (CourseRole.TA, "Teaching Assistant"),
        (CourseRole.OBSERVER, "Observer"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="memberships")
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)

    class Meta:
        db_table = "lms_course_membership"
        ordering = ["course", "role", "user_id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "user_id"], name="lms_membership_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "role"], name="lms_mem_user_role_idx"),
            models.Index(fields=["course", "role"], name="lms_mem_course_role_idx"),
        ]

    def __str__(self) -> str:
        return f"User({self.user_id}) in {self.course.code} as {self.role}"


class CourseMaterial(TimeStampedModel):
    """A course material item: file, link, or note.

    Organized into modules or weekly sections, with support for draft,
    immediate publication, and scheduled future release (CFR-LMS-003,
    BR-LMS-005, BR-LMS-006).
    """

    TYPE_CHOICES = [
        (MaterialType.FILE, "File"),
        (MaterialType.LINK, "Link"),
        (MaterialType.NOTE, "Note"),
    ]

    SECTION_CHOICES = [
        (SectionType.MODULE, "Module"),
        (SectionType.WEEK, "Weekly Section"),
    ]

    STATUS_CHOICES = [
        (MaterialStatus.DRAFT, "Draft"),
        (MaterialStatus.PUBLISHED, "Published"),
        (MaterialStatus.SCHEDULED, "Scheduled"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=MaterialType.FILE)
    section_type = models.CharField(
        max_length=16, choices=SECTION_CHOICES, default=SectionType.MODULE
    )
    section_title = models.CharField(max_length=100, db_index=True)
    file = models.FileField(upload_to="lms/materials/%Y/%m/", null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=MaterialStatus.PUBLISHED
    )
    release_at = models.DateTimeField(null=True, blank=True, db_index=True)
    order = models.IntegerField(default=0)
    created_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "lms_course_material"
        ordering = ["section_title", "order", "-created_at"]
        indexes = [
            models.Index(fields=["course", "status"], name="lms_mat_course_status_idx"),
            models.Index(fields=["course", "section_title"], name="lms_mat_course_sec_idx"),
            models.Index(fields=["status", "release_at"], name="lms_mat_status_rel_idx"),
        ]

    def __str__(self) -> str:
        return f"Material({self.title}) in {self.course.code} [{self.material_type}]"


class CourseAnnouncement(TimeStampedModel):
    """Course-wide announcement posted by authorized faculty/staff.

    Timestamped and visible to all users enrolled in or linked to the course
    (CFR-LMS-005, AFR-LMS-005.1, AFR-LMS-005.3, AFR-LMS-005.4, BR-LMS-008).
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by_user_id = models.IntegerField(db_index=True)
    author_role = models.CharField(max_length=16, default=CourseRole.FACULTY)

    class Meta:
        db_table = "lms_course_announcement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["course", "-created_at"], name="lms_ann_course_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Announcement({self.title}) in {self.course.code}"


class CourseAssignment(TimeStampedModel):
    """A course assignment offering in the LMS.

    Captures due date, instructions, submission type, and points possible,
    with draft state before publication and release date visibility control
    (CFR-LMS-006, CFR-LMS-007, BR-LMS-009, BR-LMS-010, BR-LMS-011).
    """

    SUBMISSION_CHOICES = [
        (SubmissionType.FILE, "File Upload"),
        (SubmissionType.TEXT, "Text Entry"),
        (SubmissionType.LINK, "Website Link"),
    ]

    STATUS_CHOICES = [
        (AssignmentStatus.DRAFT, "Draft"),
        (AssignmentStatus.PUBLISHED, "Published"),
        (AssignmentStatus.SCHEDULED, "Scheduled"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    submission_type = models.CharField(
        max_length=16, choices=SUBMISSION_CHOICES, default=SubmissionType.FILE
    )
    points_possible = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("100.00")
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=AssignmentStatus.DRAFT
    )
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    release_at = models.DateTimeField(null=True, blank=True, db_index=True)
    closes_at = models.DateTimeField(null=True, blank=True, db_index=True)
    allow_late = models.BooleanField(default=False)
    file = models.FileField(upload_to="lms/assignments/%Y/%m/", null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    created_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "lms_course_assignment"
        ordering = ["due_at", "-created_at"]
        indexes = [
            models.Index(fields=["course", "status"], name="lms_asg_course_status_idx"),
            models.Index(fields=["course", "due_at"], name="lms_asg_course_due_idx"),
            models.Index(fields=["status", "release_at"], name="lms_asg_status_rel_idx"),
        ]

    def __str__(self) -> str:
        return f"Assignment({self.title}) in {self.course.code} [{self.status}]"


class CourseAssignmentExtension(TimeStampedModel):
    """An approved deadline extension granted to a student for an assignment.

    Maintains student privacy and establishes the effective submission deadline
    while preserving the original assignment due date (CFR-LMS-008, AFR-LMS-009.2).
    """

    assignment = models.ForeignKey(
        CourseAssignment, on_delete=models.CASCADE, related_name="extensions"
    )
    user_id = models.IntegerField(db_index=True)
    extended_due_at = models.DateTimeField(db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    granted_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "lms_course_assignment_extension"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "user_id"],
                name="lms_asg_ext_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["assignment", "user_id"], name="lms_asg_ext_usr_idx"),
            models.Index(fields=["user_id", "extended_due_at"], name="lms_asg_ext_due_idx"),
        ]

    def __str__(self) -> str:
        return f"Extension for User({self.user_id}) on {self.assignment.title}"


class CourseSubmission(TimeStampedModel):
    """An individual student submission for an assignment.

    Captures file, text, or link submissions with timestamping, attempt history,
    and on-time vs late status determination (CFR-LMS-008, CFR-LMS-009, BR-LMS-012,
    BR-LMS-013, BR-LMS-014).
    """

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("late", "Late"),
    ]

    assignment = models.ForeignKey(
        CourseAssignment, on_delete=models.CASCADE, related_name="submissions"
    )
    student_user_id = models.IntegerField(db_index=True)
    submission_type = models.CharField(
        max_length=16, choices=CourseAssignment.SUBMISSION_CHOICES
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="submitted")
    submitted_at = models.DateTimeField(db_index=True)
    file = models.FileField(upload_to="lms/submissions/%Y/%m/", null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    content_text = models.TextField(blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    attempt_number = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "lms_course_submission"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(
                fields=["assignment", "student_user_id", "is_latest"],
                name="lms_sub_asg_std_lat_idx",
            ),
            models.Index(fields=["assignment", "status"], name="lms_sub_asg_status_idx"),
            models.Index(fields=["student_user_id", "-submitted_at"], name="lms_sub_std_date_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"Submission #{self.attempt_number} by User({self.student_user_id}) "
            f"for {self.assignment.title}"
        )
