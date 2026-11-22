"""
Contracts exposed by the Gymkhana module to other modules.
Every getter is plural (takes a sequence of IDs/keys) per ADR-0013 and architecture rules.
"""

from collections.abc import Sequence
from datetime import date
from typing import Any

from modules.gymkhana.models import Club, ClubLeadership, ClubMembership, VenueBooking


def get_clubs(club_ids: Sequence[int]) -> list[dict[str, Any]]:
    """Return public details for requested club IDs."""
    clubs = Club.objects.filter(id__in=club_ids)
    return [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "status": c.status,
            "description": c.description,
        }
        for c in clubs
    ]


def get_active_leaderships(club_ids: Sequence[int]) -> list[dict[str, Any]]:
    """Return active leadership assignments for requested club IDs."""
    leaderships = ClubLeadership.objects.filter(
        club_id__in=club_ids, is_active=True
    ).select_related("club")
    return [
        {
            "club_id": lead.club_id,
            "coordinator_id": lead.coordinator_id,
            "co_coordinator_id": lead.co_coordinator_id,
            "faculty_councillor_id": lead.faculty_councillor_id,
            "assigned_at": lead.assigned_at,
        }
        for lead in leaderships
    ]


def get_memberships(student_ids: Sequence[int]) -> list[dict[str, Any]]:
    """Return confirmed club memberships for requested student IDs."""
    memberships = ClubMembership.objects.filter(
        student_id__in=student_ids, status="confirmed"
    ).select_related("club")
    return [
        {
            "id": m.id,
            "club_id": m.club_id,
            "club_name": m.club.name,
            "student_id": m.student_id,
            "confirmed_at": m.confirmed_at,
        }
        for m in memberships
    ]


def get_venue_bookings(
    venue_names: Sequence[str], booking_dates: Sequence[date]
) -> list[dict[str, Any]]:
    """Return venue bookings for requested venues and dates."""
    bookings = VenueBooking.objects.filter(
        venue_name__in=venue_names, booking_date__in=booking_dates
    ).select_related("club")
    return [
        {
            "id": b.id,
            "club_id": b.club_id,
            "club_name": b.club.name,
            "booking_type": b.booking_type,
            "venue_name": b.venue_name,
            "booking_date": b.booking_date,
            "start_time": b.start_time,
            "end_time": b.end_time,
        }
        for b in bookings
    ]
