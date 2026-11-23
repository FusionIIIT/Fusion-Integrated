from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import IntegerRangeField
from django.contrib.postgres.fields.ranges import RangeOperators
from django.db import models
from django.db.models import F, Q
from psycopg.types.range import Range

from core.db.mixins import TimeStampedModel
from modules.phc.domain.schedules import weekly_range


class Doctor(TimeStampedModel):
    display_name = models.CharField(max_length=160)
    specialization = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_doctor"
        ordering = ["display_name", "id"]
        indexes = [models.Index(fields=["is_active", "display_name"],
                                name="phc_doctor_active_name_idx")]


class DoctorScheduleSlot(TimeStampedModel):
    class Publication(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT,
                               related_name="schedule_slots")
    day_of_week = models.PositiveSmallIntegerField()
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    week_range = IntegerRangeField(editable=False)
    publication = models.CharField(max_length=12, choices=Publication.choices,
                                   default=Publication.DRAFT)

    class Meta:
        db_table = "phc_doctor_schedule_slot"
        ordering = ["day_of_week", "starts_at", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(day_of_week__lte=6),
                                   name="phc_slot_weekday_valid"),
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")),
                                   name="phc_slot_time_order_valid"),
            ExclusionConstraint(
                name="phc_doctor_slot_no_overlap",
                expressions=[("doctor", RangeOperators.EQUAL),
                             ("week_range", RangeOperators.OVERLAPS)],
            ),
        ]
        indexes = [models.Index(fields=["publication", "day_of_week", "starts_at"],
                                name="phc_slot_public_day_idx")]

    def save(self, *args, **kwargs):
        self.starts_at = self._meta.get_field("starts_at").to_python(self.starts_at)
        self.ends_at = self._meta.get_field("ends_at").to_python(self.ends_at)
        start, end = weekly_range(self.day_of_week, self.starts_at, self.ends_at)
        self.week_range = Range(start, end, bounds="[)")
        super().save(*args, **kwargs)


class DoctorAttendance(TimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        DEPARTED = "departed", "Departed"

    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT,
                               related_name="attendance")
    attendance_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices)
    updated_by_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "phc_doctor_attendance"
        constraints = [models.UniqueConstraint(
            fields=["doctor", "attendance_date"], name="phc_doctor_attendance_day_uniq")]
        indexes = [models.Index(fields=["attendance_date", "doctor"],
                                name="phc_attendance_date_doctor_idx")]
