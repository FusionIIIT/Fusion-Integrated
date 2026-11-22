# Alerts and notification logs for VHMS.
from django.db import models
from django.db.models import Index

from core.db.mixins import TimeStampedModel


class StayAlert(TimeStampedModel):
    # System generated exceptions such as no-shows and overstays.
    booking = models.ForeignKey(
        "vh.Booking",
        on_delete=models.CASCADE,
        related_name="stay_alerts",
    )
    alert_type = models.CharField(
        max_length=20,
        choices=[("no_show", "No-show Alert"), ("overstay", "Overstay Alert")],
    )
    status = models.CharField(
        max_length=20,
        default="active",
        choices=[("active", "Active"), ("resolved", "Resolved"), ("acknowledged", "Acknowledged")],
        db_index=True,
    )
    details = models.TextField(blank=True, default="")
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_stay_alert"
        indexes = [
            Index(fields=["alert_type", "status"], name="vh_alert_type_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.alert_type} on {self.booking.booking_reference} ({self.status})"


class BookingNotificationLog(TimeStampedModel):
    # Audit log of notifications triggered during booking and stay lifecycles.
    booking = models.ForeignKey(
        "vh.Booking",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=50)
    recipient_email = models.EmailField(blank=True, default="")
    recipient_role = models.CharField(max_length=50, blank=True, default="")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_notification_log"

    def __str__(self) -> str:
        return f"{self.event_type} to {self.recipient_email}"
