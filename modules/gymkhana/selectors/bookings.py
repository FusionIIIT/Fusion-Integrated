"""Venue booking read selectors for Gymkhana."""

from __future__ import annotations

import datetime

from django.db.models import QuerySet

from core.api.exceptions import NotFoundError
from modules.gymkhana.models.booking import VenueBooking


def get_booking_by_id(booking_id: int) -> VenueBooking:
    """Return booking by ID or raise NotFound."""
    booking = VenueBooking.objects.select_related("club").filter(id=booking_id).first()
    if not booking:
        raise NotFoundError(f"Booking {booking_id} not found.")
    return booking


def list_bookings(
    venue: str | None = None,
    booking_date: datetime.date | None = None,
    club_id: int | None = None,
) -> QuerySet[VenueBooking]:
    """Filter venue bookings."""
    qs = VenueBooking.objects.select_related("club").all()
    if venue:
        qs = qs.filter(venue=venue)
    if booking_date:
        qs = qs.filter(booking_date=booking_date)
    if club_id:
        qs = qs.filter(club_id=club_id)
    return qs


def check_venue_conflict(
    venue: str,
    booking_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    exclude_booking_id: int | None = None,
) -> bool:
    """Whether any session or event overlaps this slot (BR-GYM-006, AFR-GYM-012)."""
    # Overlap occurs when start_time < existing.end_time AND end_time > existing.start_time
    qs = VenueBooking.objects.filter(
        venue=venue,
        booking_date=booking_date,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude_booking_id:
        qs = qs.exclude(id=exclude_booking_id)
    return qs.exists()
