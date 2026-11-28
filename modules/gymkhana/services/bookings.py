"""Session and event booking (UC-GYM-002, UC-GYM-003) behind one venue-day lock (BR-GYM-006)."""
from __future__ import annotations

from datetime import date, time

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.gymkhana.domain import rules
from modules.gymkhana.domain.rules import RuleViolation, Slot
from modules.gymkhana.models import Booking, Club, VenueDay
from modules.gymkhana.selectors import scoping
from modules.gymkhana.selectors.clubs import confirmed_member_ids
from modules.gymkhana.selectors.venues import current_venue_names
from modules.gymkhana.services import audit, links, notifications, people
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import refused
from modules.gymkhana.services.inputs import NOT_LED, required_text

P_BOOK = "gymkhana.booking.create"


def _venue(requested: str) -> str:
    """BR-GYM-020: the canonical name from the list in effect, or a refusal saying what to pick."""
    names = current_venue_names()
    if not names:
        raise ConflictError("No Gymkhana venues are configured yet, so nothing can be "
                            "booked. Ask the module operator to seed the venue list.",
                            code="no_venues_configured")
    wanted = (requested or "").strip().casefold()
    for name in names:
        if name.casefold() == wanted:
            return name
    raise DomainError("Choose one of the configured venues.", code="unknown_venue",
                      details=[{"field": "venue", "message": "Not a configured venue."}])


def _check_slot(day: date, start: time, end: time) -> None:
    """BR-GYM-005 and the booking-date window."""
    try:
        rules.check_time_range(start, end)
        rules.check_booking_date(day, timezone.localdate())
    except RuleViolation as exc:
        raise refused(exc) from exc


def _event_faculty(club: Club) -> int:
    """BR-GYM-002 in event context: the club's assigned councillor, still valid faculty."""
    try:
        people.require_faculty({"faculty_councillor_user_id": club.faculty_councillor_user_id})
    except DomainError as exc:
        raise ConflictError(
            "The club's faculty councillor is no longer listed as faculty, so an "
            "event cannot be booked. Ask Student Admin to review the club.",
            code="councillor_invalid", details=exc.details) from exc
    return club.faculty_councillor_user_id


def _reserve(venue_name: str, day: date, start: time, end: time) -> None:
    """BR-GYM-006: lock the venue-day, then refuse any overlap with what is already there."""
    VenueDay.objects.get_or_create(venue_name=venue_name, date=day)
    VenueDay.objects.select_for_update().get(venue_name=venue_name, date=day)
    taken = Booking.objects.filter(venue_name=venue_name, date=day).values_list(
        "pk", "start_time", "end_time")
    clash = rules.find_conflict(start, end, (Slot(*row) for row in taken))
    if clash is not None:
        raise ConflictError(
            f"{venue_name} is already booked from {clash.start:%H:%M} to "
            f"{clash.end:%H:%M} on {day:%d %b %Y}. Choose another time or venue.",
            code="venue_slot_taken")


@transaction.atomic
def _book(*, actor, kind: str, club_id: int, venue: str, day: date, start: time,
          end: time, description: str, poster_url: str = "",
          event_name: str = "") -> Booking:
    require(actor, P_BOOK)
    club = scoping.led_clubs(actor).filter(pk=club_id).first()
    if club is None:
        raise NotFoundError(NOT_LED)
    is_event = kind == Booking.EVENT
    _check_slot(day, start, end)
    description = required_text(description, "description", "Describe the booking.")
    if is_event:
        event_name = required_text(event_name, "event_name", "Enter the event's name.")
    poster = links.parse_link(
        poster_url, field="poster_url", missing_code="poster_required",
        missing_message="An event needs a poster. Paste its Google Drive link.",
        required=is_event)
    faculty_id = _event_faculty(club) if is_event else None
    venue_name = _venue(venue)
    _reserve(venue_name, day, start, end)
    booking = Booking.objects.create(
        club=club, kind=kind, venue_name=venue_name, date=day, start_time=start,
        end_time=end, description=description,
        poster_link=poster.url if poster else "",
        poster_file_id=poster.file_id if poster else "", event_name=event_name,
        faculty_user_id=faculty_id, created_by_user_id=actor.user_id)
    audit.record(f"{kind}.booked", object_type="booking", object_id=booking.pk,
                 actor=actor, club_id=club.pk)
    _notify(booking, club)
    return booking


def _notify(booking: Booking, club: Club) -> None:
    """AFR-GYM-013/015: the club's confirmed members (ruling R6)."""
    what = booking.event_name or "A club session"
    topic = (notifications.EVENT_BOOKED if booking.kind == Booking.EVENT
             else notifications.SESSION_BOOKED)
    notifications.enqueue_to_users(
        topic=topic, key=f"{topic}:{booking.pk}",
        subject=f"{club.name}: {what} on {booking.date:%d %b %Y}",
        body=(f"{what} of {club.name} is booked at {booking.venue_name} on "
              f"{booking.date:%d %b %Y}, {booking.start_time:%H:%M} to "
              f"{booking.end_time:%H:%M}."),
        user_ids=confirmed_member_ids(club.pk),
        payload={"booking_id": booking.pk, "club_id": club.pk})


def book_session(*, actor, club_id: int, venue: str, date: date, start_time: time,
                 end_time: time, description: str, poster_url: str = "") -> Booking:
    return _book(actor=actor, kind=Booking.SESSION, club_id=club_id, venue=venue,
                 day=date, start=start_time, end=end_time, description=description,
                 poster_url=poster_url)


def book_event(*, actor, club_id: int, event_name: str, venue: str, date: date,
               start_time: time, end_time: time, description: str,
               poster_url: str) -> Booking:
    return _book(actor=actor, kind=Booking.EVENT, club_id=club_id, venue=venue,
                 day=date, start=start_time, end=end_time, description=description,
                 poster_url=poster_url, event_name=event_name)
