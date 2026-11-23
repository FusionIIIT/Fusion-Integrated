"""Scoping and authorization checks for Gymkhana."""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.gymkhana.domain.constants import CLUB_STATUS_CONFIRMED
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.report import ClubEventReport


def is_club_head(user_id: int, club: Club) -> bool:
    """Return True if user is the active coordinator or co-coordinator (BR-GYM-010)."""
    return club.coordinator_id == user_id or club.co_coordinator_id == user_id


def is_faculty_councillor(user_id: int, club: Club) -> bool:
    """Return True if user is the assigned Club Faculty Councillor (BR-GYM-021)."""
    return club.faculty_councillor_id == user_id


def is_student_admin(roles: Sequence[str]) -> bool:
    """Return True if user holds the student_admin role."""
    return "student_admin" in roles


def scope_clubs(user_id: int, roles: Sequence[str]) -> QuerySet[Club]:
    """Student Admin sees all clubs; normal users see only confirmed clubs."""
    if is_student_admin(roles):
        return Club.objects.all()
    # Also allow club coordinators to see their own open club
    return Club.objects.filter(
        Q(status=CLUB_STATUS_CONFIRMED) | Q(coordinator_id=user_id) | Q(co_coordinator_id=user_id)
    ).distinct()


def scope_memberships(
    user_id: int, roles: Sequence[str], club_id: int | None = None
) -> QuerySet[ClubMembership]:
    """Club heads see memberships for their club; students see their own memberships."""
    qs = ClubMembership.objects.select_related("club")
    if club_id:
        club = Club.objects.filter(id=club_id).first()
        if club and is_club_head(user_id, club):
            return qs.filter(club_id=club_id)
        if is_student_admin(roles):
            return qs.filter(club_id=club_id)
    # Default: student sees their own
    return qs.filter(student_id=user_id)


def scope_budget_requests(
    user_id: int, roles: Sequence[str], club_id: int | None = None
) -> QuerySet[ClubBudgetRequest]:
    """Club heads see their club's budget requests; Student Admin sees all."""
    qs = ClubBudgetRequest.objects.select_related("club")
    if is_student_admin(roles):
        if club_id:
            return qs.filter(club_id=club_id)
        return qs.all()
    if club_id:
        club = Club.objects.filter(id=club_id).first()
        if club and is_club_head(user_id, club):
            return qs.filter(club_id=club_id)
        raise NotFoundError("Budget requests not found.")
    # Find all clubs where user is head
    head_club_ids = Club.objects.filter(
        Q(coordinator_id=user_id) | Q(co_coordinator_id=user_id)
    ).values_list("id", flat=True)
    return qs.filter(club_id__in=head_club_ids)


def scope_event_reports(
    user_id: int, roles: Sequence[str], club_id: int | None = None
) -> QuerySet[ClubEventReport]:
    """Faculty Councillor, Club Head, and Student Admin access event reports."""
    qs = ClubEventReport.objects.select_related("club")
    if is_student_admin(roles):
        if club_id:
            return qs.filter(club_id=club_id)
        return qs.all()
    if club_id:
        club = Club.objects.filter(id=club_id).first()
        if not club:
            raise NotFoundError("Club not found.")
        if is_faculty_councillor(user_id, club) or is_club_head(user_id, club):
            return qs.filter(club_id=club_id)
        raise NotFoundError("Event reports not found.")
    # Return reports for all clubs where user is councillor or head
    accessible_clubs = Club.objects.filter(
        Q(faculty_councillor_id=user_id) | Q(coordinator_id=user_id) | Q(co_coordinator_id=user_id)
    ).values_list("id", flat=True)
    return qs.filter(club_id__in=accessible_clubs)
