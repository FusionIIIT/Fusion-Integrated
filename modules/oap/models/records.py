from django.db import models


class SupervisorAssignment(models.Model):
    student_id = models.IntegerField(unique=True)
    faculty_id = models.IntegerField()
    assigned_by_id = models.IntegerField()
    decision_reference = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Supervisor {self.faculty_id} for student {self.student_id}"


class TAAssignment(models.Model):
    """A TA assignment names a course, a faculty member, or both (OA-UC-42)."""

    student_id = models.IntegerField(db_index=True)
    course_code = models.CharField(max_length=20, blank=True)
    faculty_id = models.IntegerField(null=True, blank=True)
    assigned_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"TA assignment for student {self.student_id}"
