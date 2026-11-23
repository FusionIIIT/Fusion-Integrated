"""Venue booking services for Gymkhana."""

from __future__ import annotations

import datetime

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.contracts import get_users
from modules.gymkhana.domain.constants import (
    BOOKING_TYPE_EVENT,
    BOOKING_TYPE_SESSION,
    CLUB_STATUS_CONFIRMED,
    POSTER_EXTENSIONS,
)
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.validation import validate_booking_times, validate_venue
from modules.gymkhana.models.booking import VenueBooking, VenueDay
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.bookings import check_venue_conflict
from modules.gymkhana.selectors.scoping import is_club_head
from modules.gymkhana.selectors.venues import configured_venues
from modules.gymkhana.services.notifications import announce_booking
from modules.gymkhana.services.uploads import check_upload


def book_session(
    *,
    club_id: int,
    actor_id: int,
    venue: str,
    booking_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    description: str,
    poster_file=None,
    name: str = "",
) -> VenueBooking:
    """Book a club session (UC-GYM-002, AFR-GYM-010)."""
    return _book(
        booking_type=BOOKING_TYPE_SESSION,
        club_id=club_id,
        actor_id=actor_id,
        venue=venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        name=name,
        description=description,
        poster_file=poster_file,
        faculty_councillor_id=None,
    )


def book_event(
    *,
    club_id: int,
    actor_id: int,
    venue: str,
    booking_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    name: str,
    description: str,
    faculty_councillor_id: int,
    poster_file=None,
) -> VenueBooking:
    """Book a club event with its faculty context (UC-GYM-003, AFR-GYM-014)."""
    return _book(
        booking_type=BOOKING_TYPE_EVENT,
        club_id=club_id,
        actor_id=actor_id,
        venue=venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        name=name,
        description=description,
        poster_file=poster_file,
        faculty_councillor_id=faculty_councillor_id,
    )


@transaction.atomic
def _book(
    *,
    booking_type: str,
    club_id: int,
    actor_id: int,
    venue: str,
    booking_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    name: str,
    description: str,
    poster_file,
    faculty_councillor_id: int | None,
) -> VenueBooking:
    """The one path to a booking, whatever its type (CFR-GYM-003, BR-GYM-006, BR-GYM-010)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")
    if not is_club_head(actor_id, club):
        raise PermissionDeniedError(f"Only the active Club Head can book a {booking_type}.")
    if club.status != CLUB_STATUS_CONFIRMED:
        raise ConflictError(f"A {booking_type} can only be booked for a confirmed club.")

    try:
        validate_booking_times(start_time, end_time)
        clean_venue = validate_venue(venue, configured_venues())
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc
    if booking_type == BOOKING_TYPE_EVENT:
        _verify_faculty(faculty_councillor_id)
    if poster_file:
        check_upload(poster_file, POSTER_EXTENSIONS)

    # Locking a row that always exists serialises bookings even when the day is empty (BR-GYM-006).
    VenueDay.objects.get_or_create(venue=clean_venue, booking_date=booking_date)
    VenueDay.objects.select_for_update().get(venue=clean_venue, booking_date=booking_date)
    if check_venue_conflict(clean_venue, booking_date, start_time, end_time):
        raise ConflictError(
            f"Venue '{clean_venue}' is already booked on {booking_date} during that time. "
            f"Select another slot."
        )

    booking = VenueBooking.objects.create(
        club=club,
        booking_type=booking_type,
        venue=clean_venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        name=name.strip() or f"{club.name} Session",
        description=description.strip(),
        faculty_councillor_id=faculty_councillor_id,
        poster_file=poster_file,
        booked_by_id=actor_id,
    )
    announce_booking(booking)
    return booking


def _verify_faculty(faculty_councillor_id: int | None) -> None:
    """The event names a valid faculty member (BR-GYM-002, AFR-GYM-003)."""
    user = get_users([faculty_councillor_id]).get(faculty_councillor_id)
    if not user or user.kind != "faculty":
        raise BadRequestError(f"User {faculty_councillor_id} is not a valid faculty member.")
