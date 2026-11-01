from django.db import models

from core.db.mixins import TimeStampedModel


class DoctorSchedule(TimeStampedModel):
    doctor_name = models.CharField(max_length=120)
    specialization = models.CharField(max_length=80, blank=True)
    day_of_week = models.PositiveSmallIntegerField(
        choices=[
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),
        ]
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    published = models.BooleanField(default=False)
    is_present = models.BooleanField(default=False)

    class Meta:
        db_table = "phc_doctor_schedule"
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(
                name="phc_schedule_end_after_start",
                check=models.Q(end_time__gt=models.F("start_time")),
            ),
        ]


class Visit(TimeStampedModel):
    patient_id = models.PositiveIntegerField(db_index=True)
    schedule = models.ForeignKey(
        DoctorSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits",
    )
    visit_date = models.DateField()
    complaint = models.TextField()
    diagnosis = models.TextField(blank=True)
    recorded_by = models.PositiveIntegerField()

    class Meta:
        db_table = "phc_visit"
        ordering = ["-visit_date"]


class Prescription(TimeStampedModel):
    visit = models.ForeignKey(
        Visit, on_delete=models.CASCADE, related_name="prescriptions"
    )
    medicine = models.CharField(max_length=120)
    dosage = models.CharField(max_length=80)
    duration_days = models.PositiveSmallIntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "phc_prescription"
