"""Venue booking services for Gymkhana."""

from __future__ import annotations

import datetime

from django.conf import settings
from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.contracts import get_users
from modules.gymkhana.domain.constants import (
    BOOKING_TYPE_EVENT,
    BOOKING_TYPE_SESSION,
    CLUB_STATUS_CONFIRMED,
)
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.validation import (
    validate_booking_times,
    validate_venue,
)
from modules.gymkhana.models.booking import VenueBooking
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.scoping import is_club_head


def _get_configured_venues() -> list[str]:
    return getattr(
        settings,
        "GYMKHANA_CONFIGURED_VENUES",
        [
            "Hall 1",
            "Hall 2",
            "L-101",
            "L-102",
            "Open Air Theatre",
            "SAC Gym",
            "Football Ground",
            "Basketball Court",
            "Badminton Court",
            "Volleyball Court",
        ],
    )


@transaction.atomic
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
    """Book a club session with venue conflict prevention (UC-GYM-002, AFR-GYM-010 to 013)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    if not is_club_head(actor_id, club):
        raise PermissionDeniedError("Only the active Club Head can book a session.")

    if club.status != CLUB_STATUS_CONFIRMED:
        raise ConflictError("Sessions can only be booked for confirmed clubs.")

    try:
        validate_booking_times(start_time, end_time)
        clean_venue = validate_venue(venue, _get_configured_venues())
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc

    # Enforce cross-type exclusivity (BR-GYM-006) under table lock
    overlapping = (
        VenueBooking.objects.select_for_update()
        .filter(
            venue=clean_venue,
            booking_date=booking_date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        .exists()
    )
    if overlapping:
        raise ConflictError(
            f"Venue '{clean_venue}' is already booked on {booking_date} during that time."
        )

    return VenueBooking.objects.create(
        club=club,
        booking_type=BOOKING_TYPE_SESSION,
        venue=clean_venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        name=name.strip() or f"{club.name} Session",
        description=description.strip(),
        poster_file=poster_file,
        booked_by_id=actor_id,
    )


@transaction.atomic
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
    """Book an event with venue conflict check and faculty context (UC-GYM-003)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    if not is_club_head(actor_id, club):
        raise PermissionDeniedError("Only the active Club Head can book an event.")

    if club.status != CLUB_STATUS_CONFIRMED:
        raise ConflictError("Events can only be booked for confirmed clubs.")

    try:
        validate_booking_times(start_time, end_time)
        clean_venue = validate_venue(venue, _get_configured_venues())
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc

    # Validate faculty councillor context (BR-GYM-002, AFR-GYM-003)
    users = get_users([faculty_councillor_id])
    fc = users.get(faculty_councillor_id)
    if not fc or fc.kind != "faculty":
        raise BadRequestError(f"User {faculty_councillor_id} is not a valid faculty member.")

    overlapping = (
        VenueBooking.objects.select_for_update()
        .filter(
            venue=clean_venue,
            booking_date=booking_date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        .exists()
    )
    if overlapping:
        raise ConflictError(
            f"Venue '{clean_venue}' is already booked on {booking_date} during that time."
        )

    return VenueBooking.objects.create(
        club=club,
        booking_type=BOOKING_TYPE_EVENT,
        venue=clean_venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        name=name.strip(),
        description=description.strip(),
        faculty_councillor_id=faculty_councillor_id,
        poster_file=poster_file,
        booked_by_id=actor_id,
    )
