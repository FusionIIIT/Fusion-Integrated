from django.db import models

from core.db.mixins import TimeStampedModel


class TimetableSlot(TimeStampedModel):
    """Represents a specific slot in the timetable."""
    slot_kind = models.CharField(max_length=10, choices=[('class', 'Class'), ('lab', 'Lab')])
    weekday = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100)
    faculty_user_id = models.IntegerField(null=True, blank=True)
    programme = models.CharField(max_length=100, blank=True)
    batch_year = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)

    class Meta:
        db_table = 'department_timetable_slot'
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name='dept_slot_time_order'
            )
        ]

class LabResource(TimeStampedModel):
    """Represents a specific lab resource."""
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    equipment = models.CharField(max_length=100, blank=True)
    capacity = models.IntegerField(default=0)
    location = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'department_lab_resource'

class AcademicProgram(TimeStampedModel):
    """Represents an academic program."""
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'department_academic_program'
