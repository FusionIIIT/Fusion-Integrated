"""Doctor, Master Schedule and Live Attendance models."""
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class Doctor(TimeStampedModel):
    name = models.CharField(max_length=120)
    specialization = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_visiting = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_doctors"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"Dr. {self.name} ({self.specialization})"


class DoctorSchedule(TimeStampedModel):
    """Static/master weekly schedule (AFR-PHC-002, 004, 005; UC-PHC-07, 22)."""
    DAYS_OF_WEEK = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="schedules")
    day_of_week = models.CharField(max_length=15, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=30, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "phc_doctor_schedules"
        ordering = ["day_of_week", "start_time"]

    def __str__(self) -> str:
        return f"{self.doctor.name} - {self.day_of_week} ({self.start_time} to {self.end_time})"


class DoctorAttendance(TimeStampedModel):
    """Current-day real-time attendance status (AFR-PHC-003; UC-PHC-08; BR-PHC-01)."""
    STATUS_CHOICES = [
        ("Available", "Available"),
        ("Departed", "Departed"),
        ("On-Leave", "On-Leave"),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Available")
    marked_by_user_id = models.IntegerField()
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "phc_doctor_attendance"
        unique_together = ("doctor", "date")
        ordering = ["-date", "doctor__name"]

    def __str__(self) -> str:
        return f"{self.doctor.name} on {self.date}: {self.status}"
