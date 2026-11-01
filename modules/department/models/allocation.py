"""Departmental supervisor and TA allocation models (AFR-OAP-043, AFR-OAP-044)."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class ThesisSupervisorAllocation(TimeStampedModel):
    """Departmental thesis supervisor allocation record (AFR-OAP-043)."""
    student_id = models.IntegerField(db_index=True)
    student_name = models.CharField(max_length=150)
    programme = models.CharField(max_length=60, default="M.Tech")
    department = models.CharField(max_length=80, blank=True)
    supervisor_id = models.IntegerField(db_index=True)
    supervisor_name = models.CharField(max_length=150)
    co_supervisor_name = models.CharField(max_length=150, blank=True)
    thesis_topic = models.CharField(max_length=255, blank=True)
    academic_year = models.CharField(max_length=20, default="2026-27")
    status = models.CharField(max_length=30, default="ACTIVE")

    class Meta:
        db_table = "department_supervisor_allocation"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["supervisor_id"]),
        ]

    def __str__(self) -> str:
        return f"Supervisor: {self.student_name} -> {self.supervisor_name} ({self.academic_year})"


class TAAllocation(TimeStampedModel):
    """Departmental teaching assistant allocation record (AFR-OAP-044)."""
    student_id = models.IntegerField(db_index=True)
    student_name = models.CharField(max_length=150)
    programme = models.CharField(max_length=60, default="M.Tech")
    department = models.CharField(max_length=80, blank=True)
    course_code = models.CharField(max_length=20, db_index=True)
    course_name = models.CharField(max_length=150)
    faculty_id = models.IntegerField(null=True, blank=True, db_index=True)
    faculty_name = models.CharField(max_length=150, blank=True)
    semester = models.CharField(max_length=20, default="Monsoon")
    academic_year = models.CharField(max_length=20, default="2026-27")
    hours_per_week = models.PositiveSmallIntegerField(default=8)

    class Meta:
        db_table = "department_ta_allocation"
        indexes = [
            models.Index(fields=["student_id", "academic_year"]),
            models.Index(fields=["course_code"]),
        ]

    def __str__(self) -> str:
        return f"TA: {self.student_name} for {self.course_code} ({self.semester} {self.academic_year})"
