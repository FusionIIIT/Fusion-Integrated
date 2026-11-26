from django.db import models

from core.db.mixins import TimeStampedModel


class DepartmentProfile(TimeStampedModel):
    """Stores profile information for individuals associated with a department."""
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)
    record_kind = models.CharField(
        max_length=10,
        choices=[
            ('faculty', 'Faculty'),
            ('student', 'Student'),
            ('alumni', 'Alumni'),
        ],
    )
    user_id = models.IntegerField(null=True, blank=True)
    display_name = models.TextField(blank=True)
    email = models.TextField(blank=True)
    title = models.TextField(blank=True)
    office = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'department_profile'

class CourseRoster(TimeStampedModel):
    """Tracks which faculty teach which students in a specific course and year."""
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)
    course_code = models.CharField(max_length=50)
    faculty_user_id = models.IntegerField()
    student_user_id = models.IntegerField()
    academic_year = models.CharField(max_length=10)

    class Meta:
        db_table = 'department_course_roster'
        unique_together = (
            ('course_code', 'faculty_user_id', 'student_user_id', 'academic_year'),
        )
        constraints = [
            models.UniqueConstraint(
                fields=['course_code', 'faculty_user_id', 'student_user_id', 'academic_year'],
                name='dept_roster_unique',
            )
        ]

class OfficialChangeProposal(TimeStampedModel):
    """Manages proposals for official changes within the department."""
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)
    changes = models.JSONField()
    state = models.CharField(
        max_length=20,
        choices=[
            ('pending_hod_approval', 'Pending HOD Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending_hod_approval',
    )
    proposed_by_user_id = models.IntegerField()
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'department_official_change'
