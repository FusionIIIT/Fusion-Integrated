from django.db import models

from core.db.mixins import TimeStampedModel


class AmbulanceUsage(TimeStampedModel):
    used_at = models.DateTimeField()
    patient_name = models.CharField(max_length=160)
    destination = models.CharField(max_length=200)
    recorded_by_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "phc_ambulance_usage"
        ordering = ["-used_at", "-id"]
        indexes = [models.Index(fields=["-used_at"], name="phc_ambulance_used_at_idx")]


class HealthAdvisory(TimeStampedModel):
    title = models.CharField(max_length=180)
    body = models.TextField()
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "phc_health_advisory"
        ordering = ["-published_at", "-id"]
        indexes = [models.Index(fields=["-published_at", "-id"],
                                name="phc_advisory_published_idx")]
