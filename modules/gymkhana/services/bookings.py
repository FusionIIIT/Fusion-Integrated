from datetime import date, time

from django.db import transaction

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.gymkhana.domain.constants import BOOKING_EVENT, BOOKING_SESSION
from modules.gymkhana.domain.validation import validate_booking_time_range, validate_venue
from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.bookings import has_venue_overlap
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def book_activity(
    *,
    club_id: int,
    acting_user_id: int,
    booking_type: str,
    title: str,
    venue: str,
    booking_date: date,
    start_time: time,
    end_time: time,
    description: str = "",
) -> ClubBooking:
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    if not is_club_head(acting_user_id, club_id):
        raise PermissionDeniedError(
            "Only the current club coordinator or co-coordinator may book activities.",
            code="not_club_head",
        )

    try:
        validate_booking_time_range(start_time, end_time)
        validate_venue(venue)
    except ValueError as e:
        raise BadRequestError(str(e), code="invalid_booking_details") from e

    if has_venue_overlap(venue, booking_date, start_time, end_time):
        msg = (
            f"Venue {venue} is already booked on {booking_date} "
            f"between {start_time} and {end_time}."
        )
        raise ConflictError(msg, code="venue_booking_conflict")

    return ClubBooking.objects.create(
        club=club,
        booking_type=booking_type,
        title=title,
        venue=venue,
        date=booking_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        created_by_id=acting_user_id,
    )


def book_session(
    *,
    club_id: int,
    acting_user_id: int,
    title: str,
    venue: str,
    booking_date: date,
    start_time: time,
    end_time: time,
    description: str = "",
) -> ClubBooking:
    return book_activity(
        club_id=club_id,
        acting_user_id=acting_user_id,
        booking_type=BOOKING_SESSION,
        title=title,
        venue=venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
    )


def book_event(
    *,
    club_id: int,
    acting_user_id: int,
    title: str,
    venue: str,
    booking_date: date,
    start_time: time,
    end_time: time,
    description: str = "",
) -> ClubBooking:
    return book_activity(
        club_id=club_id,
        acting_user_id=acting_user_id,
        booking_type=BOOKING_EVENT,
        title=title,
        venue=venue,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
    )
