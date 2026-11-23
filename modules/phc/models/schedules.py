from django.db import models

from core.db.mixins import TimeStampedModel


class DoctorSchedule(TimeStampedModel):
    doctor_name = models.CharField(max_length=160)
    specialization = models.CharField(max_length=120, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_doctor_schedule"
        indexes = [
            models.Index(fields=["is_published", "doctor_name"],
                         name="phc_schedule_published_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_published=False) | models.Q(published_at__isnull=False),
                name="phc_schedule_published_has_time"),
        ]

    def __str__(self) -> str:
        return self.doctor_name


class ScheduleSlot(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    schedule = models.ForeignKey(DoctorSchedule, on_delete=models.CASCADE,
                                 related_name="slots")
    day_of_week = models.PositiveSmallIntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = "phc_schedule_slot"
        ordering = ("day_of_week", "start_time")
        constraints = [
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")),
                                   name="phc_slot_end_after_start"),
            models.CheckConstraint(condition=models.Q(day_of_week__lte=6),
                                   name="phc_slot_day_in_week"),
            models.UniqueConstraint(fields=("schedule", "day_of_week", "start_time"),
                                    name="phc_slot_unique_start"),
        ]

    def __str__(self) -> str:
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class DoctorAttendance(TimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        DEPARTED = "departed", "Departed"

    schedule = models.ForeignKey(DoctorSchedule, on_delete=models.CASCADE,
                                 related_name="attendance")
    attendance_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices)
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_doctor_attendance"
        indexes = [
            models.Index(fields=["attendance_date", "schedule"],
                         name="phc_attendance_day_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("schedule", "attendance_date"),
                                    name="phc_attendance_once_per_day"),
        ]

    def __str__(self) -> str:
        return f"{self.schedule_id} {self.attendance_date} {self.status}"
