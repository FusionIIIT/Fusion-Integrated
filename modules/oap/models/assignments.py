from django.db import models

from core.db.mixins import TimeStampedModel


class ThesisSupervisorAssignment(TimeStampedModel):
    """Departmental assignment of thesis supervisor to PG student (OA-UC-41, OA-BR-51)."""

    student_user_id = models.IntegerField(db_index=True)
    supervisor_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100)
    assigned_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class TeachingAssistantAssignment(TimeStampedModel):
    """Departmental assignment of PG student as TA (OA-UC-42, OA-BR-51, OA-BR-52)."""

    student_user_id = models.IntegerField(db_index=True)
    ta_supervisor_user_id = models.IntegerField(db_index=True, null=True, blank=True)
    course_code = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=20, blank=True)
    year = models.IntegerField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
