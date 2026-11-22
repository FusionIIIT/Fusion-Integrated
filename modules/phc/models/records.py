from django.db import models

from core.db.mixins import TimeStampedModel


class PatientVisit(TimeStampedModel):
    patient_user_id = models.IntegerField()
    visit_date = models.DateField()
    complaint = models.TextField()
    diagnosis = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_patient_visit"
        indexes = [
            models.Index(fields=["patient_user_id", "-visit_date"],
                         name="phc_visit_patient_idx"),
            models.Index(fields=["visit_date"], name="phc_visit_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(patient_user_id=models.F(
                "recorded_by_user_id")), name="phc_visit_not_self_recorded"),
        ]

    def __str__(self) -> str:
        return f"Visit {self.pk} on {self.visit_date}"


class Prescription(TimeStampedModel):
    visit = models.ForeignKey(PatientVisit, on_delete=models.PROTECT,
                              related_name="prescriptions")
    medicine = models.CharField(max_length=160)
    dosage = models.CharField(max_length=120)
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)
    instructions = models.TextField(blank=True)

    class Meta:
        db_table = "phc_prescription"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.medicine} ({self.dosage})"
