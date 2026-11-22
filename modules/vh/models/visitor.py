# Visitor detail entity for VHMS bookings.
from django.db import models

from core.db.mixins import TimeStampedModel


class VisitorDetail(TimeStampedModel):
    # Records personal and contact details of visitors covered under a booking.
    booking = models.ForeignKey(
        "vh.Booking",
        on_delete=models.CASCADE,
        related_name="visitors",
    )
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    organization = models.CharField(max_length=150, blank=True, default="")
    designation = models.CharField(max_length=100, blank=True, default="")
    gender = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        db_table = "vh_visitor_detail"

    def __str__(self) -> str:
        return f"{self.name} ({self.booking.booking_reference})"
