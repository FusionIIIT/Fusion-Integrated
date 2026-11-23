"""Unified venue booking aggregate for Gymkhana."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint

from modules.gymkhana.domain.constants import (
    BOOKING_TYPE_SESSION,
    BOOKING_TYPES,
)
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.files import PrivateStorage, poster_key


class VenueDay(models.Model):
    """The row every booking of one venue on one date locks first (BR-GYM-006)."""

    venue = models.CharField(max_length=100)
    booking_date = models.DateField()

    class Meta:
        db_table = "gymkhana_venue_day"
        constraints = [
            UniqueConstraint(fields=["venue", "booking_date"], name="unique_gymkhana_venue_day"),
        ]

    def __str__(self) -> str:
        return f"{self.venue} on {self.booking_date}"


class VenueBooking(models.Model):
    """Unified session and event booking for cross-type venue conflict prevention."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="bookings")
    booking_type = models.CharField(max_length=20, default=BOOKING_TYPE_SESSION)
    venue = models.CharField(max_length=100)
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    name = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    poster_file = models.FileField(
        upload_to=poster_key, storage=PrivateStorage(), blank=True, null=True
    )
    faculty_councillor_id = models.IntegerField(null=True, blank=True)
    booked_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_venue_booking"
        ordering = ["booking_date", "start_time"]
        indexes = [
            models.Index(
                fields=["venue", "booking_date", "start_time"], name="gym_booking_slot_idx"
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(booking_type__in=BOOKING_TYPES),
                name="check_gymkhana_booking_type",
            ),
            CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="check_booking_start_before_end",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.booking_type.capitalize()} on {self.booking_date} at {self.venue}"
