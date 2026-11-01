"""Patient clinical visits and digitized prescriptions (CFR-PHC-002, BR-PHC-02)."""
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel
from .doctors import Doctor


class PatientVisit(TimeStampedModel):
    """Clinical visit record created by PHC Staff (AFR-PHC-007; UC-PHC-06)."""
    patient_user_id = models.IntegerField(db_index=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="visits")
    visit_date = models.DateField(default=timezone.now)
    symptoms = models.TextField()
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_patient_visits"
        ordering = ["-visit_date", "-created_at"]

    def __str__(self) -> str:
        return f"Visit #{self.id} for user {self.patient_user_id} on {self.visit_date}"


class Prescription(TimeStampedModel):
    """Digitized physical prescription linked to a visit (AFR-PHC-008, 010; UC-PHC-06)."""
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name="prescriptions")
    patient_user_id = models.IntegerField(db_index=True)
    prescription_number = models.CharField(max_length=64, unique=True, db_index=True)
    prescribed_date = models.DateField(default=timezone.now)
    medicines_prescribed = models.TextField(help_text="Medicines, dosage instructions, and duration")
    scanned_document_url = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_prescriptions"
        ordering = ["-prescribed_date", "-created_at"]

    def __str__(self) -> str:
        return f"Prescription {self.prescription_number} (Patient {self.patient_user_id})"
