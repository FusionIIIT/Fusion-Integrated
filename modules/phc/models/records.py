from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class PatientVisit(TimeStampedModel):
    patient_user_id = models.PositiveBigIntegerField()
    visited_on = models.DateField()
    notes = models.TextField()
    recorded_by_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "phc_patient_visit"
        ordering = ["-visited_on", "-id"]
        indexes = [
            models.Index(fields=["patient_user_id", "-visited_on", "-id"],
                         name="phc_visit_patient_date_idx"),
            models.Index(fields=["recorded_by_user_id", "-created_at"],
                         name="phc_visit_actor_created_idx"),
        ]
        constraints = [models.CheckConstraint(
            condition=~Q(notes=""), name="phc_visit_notes_nonempty")]


class Prescription(TimeStampedModel):
    visit = models.ForeignKey(PatientVisit, on_delete=models.PROTECT,
                              related_name="prescriptions")
    details = models.TextField()
    issued_on = models.DateField()
    issued_by_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "phc_prescription"
        ordering = ["-issued_on", "-id"]
        indexes = [models.Index(fields=["visit", "-issued_on"],
                                name="phc_rx_visit_date_idx")]
        constraints = [models.CheckConstraint(
            condition=~Q(details=""), name="phc_prescription_details_nonempty")]
