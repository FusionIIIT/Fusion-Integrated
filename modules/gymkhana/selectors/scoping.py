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
    # A club's own leaders and councillor see it before it is confirmed.
    return Club.objects.filter(
        Q(status=CLUB_STATUS_CONFIRMED)
        | Q(coordinator_id=user_id)
        | Q(co_coordinator_id=user_id)
        | Q(faculty_councillor_id=user_id)
    )


def clubs_led_by(user_id: int) -> QuerySet[Club]:
    """Clubs this person currently heads, in any status (BR-GYM-010)."""
    return Club.objects.filter(Q(coordinator_id=user_id) | Q(co_coordinator_id=user_id))


def scope_memberships(
    user_id: int, roles: Sequence[str], club_id: int | None = None
) -> QuerySet[ClubMembership]:
    """A head sees their club's applications, a student their own (AFR-GYM-020, BR-GYM-010)."""
    qs = ClubMembership.objects.select_related("club")
    if club_id:
        club = Club.objects.filter(id=club_id).first()
        if club and is_club_head(user_id, club):
            return qs.filter(club_id=club_id)
        if is_student_admin(roles):
            return qs.filter(club_id=club_id)
        qs = qs.filter(club_id=club_id)
    return qs.filter(student_id=user_id)


def reviewable_memberships(user_id: int) -> QuerySet[ClubMembership]:
    """Applications to the clubs this person heads (BR-GYM-010)."""
    return ClubMembership.objects.filter(
        Q(club__coordinator_id=user_id) | Q(club__co_coordinator_id=user_id)
    )


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


def scope_event_reports(user_id: int, club_id: int | None = None) -> QuerySet[ClubEventReport]:
    """Only the assigned councillor reads (UC-GYM-012, CFR-GYM-007, AFR-GYM-034, BR-GYM-021)."""
    qs = ClubEventReport.objects.select_related("club").filter(
        club__faculty_councillor_id=user_id
    )
    if club_id is None:
        return qs
    if not Club.objects.filter(id=club_id, faculty_councillor_id=user_id).exists():
        raise NotFoundError("Event reports not found.")
    return qs.filter(club_id=club_id)
