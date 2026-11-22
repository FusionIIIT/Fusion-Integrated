"""Registration window (BR-MMS-008/009; UC-002)."""

from django.db import models

from core.db.mixins import TimeStampedModel


class RegistrationWindow(TimeStampedModel):
    cycle_or_period = models.CharField(max_length=120)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    is_open = models.BooleanField(default=False)
    opened_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_registration_window"
        indexes = [
            models.Index(fields=["is_open"], name="registration_window_open_idx"),
        ]

    def __str__(self) -> str:
        return self.cycle_or_period
