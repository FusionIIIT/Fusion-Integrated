from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from core.db.mixins import TimeStampedModel


class TimetableSlot(TimeStampedModel):
    CLASS, LAB = "class", "lab"

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="timetable_slots"
    )
    kind = models.CharField(max_length=5, choices=[(CLASS, "Class"), (LAB, "Lab")])
    programme = models.CharField(max_length=40, blank=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    course_code = models.CharField(max_length=20)
    day_of_week = models.PositiveSmallIntegerField()
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    room = models.CharField(max_length=40, blank=True)
    # Who teaches the slot; a Student whose programme and batch match is in this course (Q2).
    instructor_user_id = models.IntegerField(null=True, blank=True)
    updated_by = models.IntegerField()

    class Meta:
        db_table = "department_timetable_slot"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="dept_slot_ends_after_start"
            ),
            models.CheckConstraint(condition=Q(day_of_week__lte=6), name="dept_slot_day_known"),
        ]
        indexes = [
            models.Index(
                fields=["department", "day_of_week", "starts_at"], name="dept_slot_week_idx"
            ),
            models.Index(
                fields=["department", "instructor_user_id"], name="dept_slot_instructor_idx"
            ),
        ]


class LabResource(TimeStampedModel):
    AVAILABLE, MAINTENANCE, RETIRED = "available", "maintenance", "retired"
    STATUS = [(AVAILABLE, "Available"), (MAINTENANCE, "Under maintenance"), (RETIRED, "Retired")]

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="lab_resources"
    )
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    equipment = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default=AVAILABLE)
    updated_by = models.IntegerField()

    class Meta:
        db_table = "department_lab_resource"
        constraints = [
            models.UniqueConstraint(Lower("name"), "department", name="dept_lab_unique_name")
        ]
        indexes = [models.Index(fields=["department", "-id"], name="dept_lab_list_idx")]


class ProfileRecord(TimeStampedModel):
    """Department-local profile supplement; identity stays with the ERP, no sensitive field (Q8)."""

    KINDS = [("faculty", "Faculty"), ("student", "Student"), ("alumni", "Alumni")]

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="profiles"
    )
    user_id = models.IntegerField(null=True, blank=True)
    kind = models.CharField(max_length=8, choices=KINDS)
    display_name = models.CharField(max_length=150)
    office = models.CharField(max_length=120, blank=True)
    research_interests = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    current_position = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.IntegerField()

    class Meta:
        db_table = "department_profile_record"
        constraints = [
            models.UniqueConstraint(
                fields=["department", "user_id"],
                condition=Q(user_id__isnull=False),
                name="dept_profile_one_per_user",
            ),
            models.CheckConstraint(
                condition=Q(kind="alumni", user_id__isnull=True)
                | (~Q(kind="alumni") & Q(user_id__isnull=False)),
                name="dept_profile_login_iff_not_alumni",
            ),
            models.CheckConstraint(condition=~Q(display_name=""), name="dept_profile_has_name"),
        ]
        indexes = [
            models.Index(
                fields=["department", "kind", "display_name"], name="dept_profile_list_idx"
            )
        ]
