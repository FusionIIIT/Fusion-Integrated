"""LMS (Course Management) domain tables.

People and students are referenced by plain `user_id` integers — no user table
exists in this database and cross-boundary references stay unconstrained per
Fusion ADR guidelines.
"""

from django.db import models
from core.db.mixins import TimeStampedModel


class CourseWorkspace(TimeStampedModel):
    """Dedicated course workspace and home page (CFR-LMS-001, UC-LMS-001, BR-LMS-001).

    Displays syllabus, schedule, instructors, and assigned TAs.
    Access restricted to enrolled/linked users per BR-LMS-001 & BR-LMS-002.
    """

    course_code = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)
    instructor_user_id = models.IntegerField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lms_course_workspace"
        indexes = [
            models.Index(fields=["course_code", "is_active"], name="lms_course_code_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.course_code} - {self.title}"


class CourseMembership(TimeStampedModel):
    """User enrollment and role linkage in a course (BR-LMS-001 to BR-LMS-004).

    Roles:
      - student: Enrolled student, can submit work, view materials & grades (BR-LMS-002).
      - faculty: Course owner, full edit, publish and grading rights.
      - ta: Teaching assistant, grades submissions, cannot create/delete assignments (BR-LMS-004).
      - observer: Read-only access to syllabus and public materials; no student data (BR-LMS-003).
    """

    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("ta", "Teaching Assistant"),
        ("observer", "Observer"),
    ]

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    can_post_announcements = models.BooleanField(default=False)  # Permitted TA per BR-LMS-004

    class Meta:
        db_table = "lms_course_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "user_id"],
                name="lms_unique_course_user_membership",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "role"], name="lms_user_role_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} in {self.course.course_code} as {self.role}"


class CourseMaterial(TimeStampedModel):
    """Course materials organized by weekly section or module (CFR-LMS-002, UC-LMS-003, BW-LMS-01).

    Lifecycle states:
      - draft: Visible only to Faculty.
      - scheduled: Future release date configured (BR-LMS-006).
      - published: Accessible to students, TAs, and observers (BR-LMS-005).
    """

    MATERIAL_TYPE = [
        ("file", "File Document"),
        ("link", "External Link"),
        ("note", "Lecture Note"),
    ]
    STATUS = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
    ]

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    section_or_week = models.CharField(max_length=100)  # e.g. "Week 1", "Module 2"
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE, default="file")
    file_url = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)
    scheduled_release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    uploaded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_course_material"
        indexes = [
            models.Index(fields=["course", "status"], name="lms_mat_course_status_idx"),
            models.Index(fields=["section_or_week"], name="lms_mat_section_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.status.upper()}] {self.title} ({self.course.course_code})"


class CourseAnnouncement(TimeStampedModel):
    """Course-wide announcements with timestamps (CFR-LMS-003, UC-LMS-005, BR-LMS-007, BR-LMS-008).

    Posted by Faculty or authorized TAs (BR-LMS-004, BR-LMS-007).
    """

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    posted_by_user_id = models.IntegerField(db_index=True)
    is_ta_announcement = models.BooleanField(default=False)
    posted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_course_announcement"
        indexes = [
            models.Index(fields=["course", "-posted_at"], name="lms_ann_course_posted_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.course.course_code} ({self.posted_at:%Y-%m-%d})"


class Assignment(TimeStampedModel):
    """Course assignment definition and lifecycle (CFR-LMS-004, UC-LMS-007, BR-LMS-009, BW-LMS-02).

    Lifecycle states (CW-LMS-01):
      - draft: Created by Faculty, not visible to students (BR-LMS-010).
      - scheduled: Configured for future release date (BR-LMS-011, BW-LMS-03).
      - available: Released and open for student submissions.
    """

    SUBMISSION_TYPE = [
        ("file", "File Upload"),
        ("text", "Text Entry"),
        ("link", "URL Link"),
    ]
    STATUS = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled for Release"),
        ("available", "Available for Submission"),
    ]

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    points_possible = models.DecimalField(max_digits=5, decimal_places=2)
    submission_type = models.CharField(max_length=20, choices=SUBMISSION_TYPE)
    due_date = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)
    scheduled_release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_assignment"
        indexes = [
            models.Index(fields=["course", "status"], name="lms_asgn_course_status_idx"),
            models.Index(fields=["due_date"], name="lms_asgn_due_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.course.course_code}) [{self.status}]"


class StudentSubmission(TimeStampedModel):
    """Student submission against an assignment (CFR-LMS-005, UC-LMS-010, BR-LMS-012, BR-LMS-013).

    Restricted so students view only their own work (BR-LMS-014).
    """

    SUBMISSION_TYPE = Assignment.SUBMISSION_TYPE
    STATUS = [
        ("submitted", "Submitted"),
        ("late", "Late Submission"),
        ("missing", "Missing"),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student_user_id = models.IntegerField(db_index=True)
    submission_type = models.CharField(max_length=20, choices=SUBMISSION_TYPE)
    submission_content = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default="submitted", db_index=True)

    class Meta:
        db_table = "lms_student_submission"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student_user_id"],
                name="lms_unique_assignment_submission",
            ),
        ]
        indexes = [
            models.Index(fields=["student_user_id", "status"], name="lms_sub_student_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Submission by u{self.student_user_id} on {self.assignment.title}"


class Grade(TimeStampedModel):
    """Grading record and feedback lifecycle (CFR-LMS-006, UC-LMS-012, BR-LMS-015 to BR-LMS-018).

    Lifecycle states (CW-LMS-02):
      - draft: Initial score & feedback by Faculty or TA, hidden from student (BR-LMS-016).
      - released: Released by Faculty, visible to student in read-only form (BR-LMS-017, BR-LMS-018).
    """

    STATUS = [
        ("draft", "Draft (Hidden from Student)"),
        ("released", "Released (Visible to Student)"),
    ]

    submission = models.OneToOneField(
        StudentSubmission,
        on_delete=models.CASCADE,
        related_name="grade",
    )
    points = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)

    graded_by_user_id = models.IntegerField()  # Faculty or TA (BR-LMS-015)
    graded_at = models.DateTimeField(auto_now=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by_user_id = models.IntegerField(null=True, blank=True)  # Must be Faculty (BR-LMS-017)

    class Meta:
        db_table = "lms_grade"
        indexes = [
            models.Index(fields=["status", "graded_by_user_id"], name="lms_grade_status_grader_idx"),
        ]

    def __str__(self) -> str:
        return f"Grade for sub #{self.submission_id}: {self.points} pts [{self.status}]"


class GradeChangeLog(TimeStampedModel):
    """Audit log for post-release grade modifications (BR-LMS-019, Section 3.6).

    Records who made the change, when, and the previous vs new points.
    """

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    old_points = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    new_points = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=500, blank=True)
    changed_by_user_id = models.IntegerField()
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_grade_change_log"
        indexes = [
            models.Index(fields=["grade", "-changed_at"], name="lms_gcl_grade_changed_idx"),
        ]

    def __str__(self) -> str:
        return f"GradeChange on #{self.grade_id}: {self.old_points} -> {self.new_points} by u{self.changed_by_user_id}"
