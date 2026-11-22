from django.db import models
from django.conf import settings
from django.utils import timezone


class Course(models.Model):
    course_code = models.CharField(max_length=20)
    course_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lms_courses"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class CourseMembership(models.Model):
    ROLE_CHOICES = [
        ("STUDENT", "Student"),
        ("FACULTY", "Faculty"),
        ("TA", "Teaching Assistant"),
        ("OBSERVER", "Observer"),
    ]

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    class Meta:
        unique_together = ("course", "user")


class CourseMaterial(models.Model):
    MATERIAL_TYPES = [
        ("FILE", "File"),
        ("LINK", "Link"),
        ("NOTE", "Note"),
    ]

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name="materials"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(
        max_length=10, choices=MATERIAL_TYPES
    )
    file = models.FileField(
        upload_to="lms/materials/", blank=True, null=True
    )
    external_link = models.URLField(blank=True)
    note_content = models.TextField(blank=True)
    module_name = models.CharField(max_length=100, blank=True)
    is_published = models.BooleanField(default=False)
    release_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_available(self):
        if not self.is_published:
            return False
        return self.release_at is None or self.release_at <= timezone.now()


class Announcement(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name="announcements"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)


class Assignment(models.Model):
    SUBMISSION_TYPES = [
        ("FILE", "File"),
        ("TEXT", "Text"),
        ("LINK", "Link"),
    ]

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name="assignments"
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    due_date = models.DateTimeField()
    total_points = models.PositiveIntegerField()
    submission_type = models.CharField(
        max_length=10, choices=SUBMISSION_TYPES
    )
    is_published = models.BooleanField(default=False)
    release_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def is_available(self):
        return (
            self.is_published and
            (self.release_at is None or self.release_at <= timezone.now())
        )


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE,
        related_name="submissions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    text_answer = models.TextField(blank=True)
    file = models.FileField(
        upload_to="lms/submissions/", blank=True, null=True
    )
    external_link = models.URLField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]


class Grade(models.Model):
    submission = models.OneToOneField(
        Submission, on_delete=models.CASCADE,
        related_name="grade"
    )
    marks = models.PositiveIntegerField()
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    is_released = models.BooleanField(default=False)
    graded_at = models.DateTimeField(auto_now=True)
    released_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.marks > self.submission.assignment.total_points:
            raise ValueError("Marks cannot exceed assignment points.")
        super().save(*args, **kwargs)