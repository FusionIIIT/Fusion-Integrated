"""Booking services with VenueDayLock concurrency engine (UC-GYM-002, UC-GYM-003, BR-GYM-006)."""
from __future__ import annotations

import datetime

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.directory import contracts as directory
from modules.gymkhana.domain.scheduling import validate_time_slot, validate_venue
from modules.gymkhana.models import Booking, Club, VenueDayLock
from modules.gymkhana.services import notifications


def acquire_venue_day_lock(venue: str, date: datetime.date) -> VenueDayLock:
    """Atomically acquire exclusive row-level lock on (venue, date) anchor (Blueprint §3.2)."""
    try:
        return VenueDayLock.objects.select_for_update().get(venue=venue, date=date)
    except VenueDayLock.DoesNotExist:
        pass

    VenueDayLock.objects.bulk_create([VenueDayLock(venue=venue, date=date)], ignore_conflicts=True)
    return VenueDayLock.objects.select_for_update().get(venue=venue, date=date)


def book_session(
    *,
    club: Club,
    venue: str,
    date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    name: str = "",
    description: str,
    poster_url: str = "",
    user_id: int,
) -> Booking:
    """Book a club session under atomic venue-day lock with cross-type exclusivity (UC-GYM-002)."""
    if user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise ConflictError(
            "Only the current club coordinator or co-coordinator may book sessions.",
            code="not_club_head",
        )

    if club.status != "confirmed":
        raise ConflictError(
            "Sessions can only be booked for confirmed clubs.",
            code="club_not_confirmed",
        )

    validate_venue(venue)
    validate_time_slot(start_time, end_time)

    with transaction.atomic():
        acquire_venue_day_lock(venue=venue, date=date)

        overlap = Booking.objects.filter(
            venue=venue,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()
        if overlap:
            raise ConflictError(
                "The venue is already booked for an overlapping time slot on this date.",
                code="venue_overlap",
            )

        booking = Booking.objects.create(
            booking_type="session",
            club=club,
            venue=venue,
            date=date,
            start_time=start_time,
            end_time=end_time,
            name=name,
            description=description,
            poster_url=poster_url,
        )
        notifications.send_session_booking_notification(booking)
        return booking


def book_event(
    *,
    club: Club,
    faculty_councillor_id: int | None = None,
    venue: str,
    date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    name: str,
    description: str,
    poster_url: str = "",
    user_id: int,
) -> Booking:
    """Book a club event under atomic venue-day lock with cross-type exclusivity (UC-GYM-003)."""
    if user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise ConflictError(
            "Only the current club coordinator or co-coordinator may book events.",
            code="not_club_head",
        )

    if club.status != "confirmed":
        raise ConflictError(
            "Events can only be booked for confirmed clubs.",
            code="club_not_confirmed",
        )

    councillor_id = faculty_councillor_id or club.faculty_councillor_id
    users = directory.get_users([councillor_id])
    faculty = users.get(councillor_id)
    if not faculty or faculty.kind != "faculty":
        raise BadRequestError(
            f"User {councillor_id} is not a valid faculty member.",
            code="invalid_faculty_councillor",
        )

    validate_venue(venue)
    validate_time_slot(start_time, end_time)

    with transaction.atomic():
        acquire_venue_day_lock(venue=venue, date=date)

        overlap = Booking.objects.filter(
            venue=venue,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()
        if overlap:
            raise ConflictError(
                "The venue is already booked for an overlapping time slot on this date.",
                code="venue_overlap",
            )

        booking = Booking.objects.create(
            booking_type="event",
            club=club,
            venue=venue,
            date=date,
            start_time=start_time,
            end_time=end_time,
            name=name,
            description=description,
            poster_url=poster_url,
            faculty_councillor_id=councillor_id,
        )
        notifications.send_event_booking_notification(booking)
        return booking
