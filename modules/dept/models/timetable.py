"""Timetable schedule model (CFR-DEPT-011, BR-DEPT-010)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class TimetableEntry(models.Model):
    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="timetables",
    )
    program = models.CharField(max_length=64)
    academic_year = models.IntegerField()
    semester = models.IntegerField()
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    course_code = models.CharField(max_length=32)
    course_name = models.CharField(max_length=255)
    instructor_id = models.CharField(max_length=64)
    room_or_lab = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_timetable_entry"
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_time__lt=models.F("end_time")),
                name="valid_timetable_time_range",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "program", "academic_year", "semester"]),
            models.Index(fields=["day_of_week", "start_time", "end_time"]),
        ]

    def __str__(self) -> str:
        return f"{self.course_code} ({self.day_of_week} {self.start_time}-{self.end_time})"
