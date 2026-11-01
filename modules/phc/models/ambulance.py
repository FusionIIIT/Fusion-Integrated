"""Ambulance usage logs (CFR-PHC-008, AFR-PHC-032; UC-PHC-11)."""
from django.db import models

from core.db.mixins import TimeStampedModel


class AmbulanceLog(TimeStampedModel):
    patient_name = models.CharField(max_length=150)
    patient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    destination = models.CharField(max_length=255)
    departure_time = models.DateTimeField()
    return_time = models.DateTimeField(null=True, blank=True)
    driver_name = models.CharField(max_length=100)
    reason = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_ambulance_logs"
        ordering = ["-departure_time"]

    def __str__(self) -> str:
        return f"Ambulance for {self.patient_name} to {self.destination} at {self.departure_time}"
