"""Who sees which rows, decided once; an out-of-scope row is absent, so asking for it is a 404."""
from __future__ import annotations

from django.db.models import Exists, OuterRef, Q, QuerySet

from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import (
    Booking,
    BudgetRequest,
    Club,
    EventReport,
    LeadershipAssignment,
    Membership,
    Poll,
)

P_CLUB_APPROVE = "gymkhana.club.approve"
P_REPORT_VIEW = "gymkhana.event_report.view"
P_REPORT_REVIEW = "gymkhana.event_report.review"


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, code: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and check(code)


def is_student_admin(actor) -> bool:
    return _has(actor, P_CLUB_APPROVE)


def current_leaders() -> QuerySet[LeadershipAssignment]:
    return LeadershipAssignment.objects.filter(valid_to__isnull=True)


def led_clubs(actor) -> QuerySet[Club]:
    """BR-GYM-010: confirmed clubs the actor is a current coordinator or co-coordinator of."""
    own = _own_id(actor)
    if own is None:
        return Club.objects.none()
    leads = current_leaders().filter(club=OuterRef("pk"), user_id=own)
    return Club.objects.filter(Exists(leads), status=sm.CONFIRMED)


def member_clubs(actor) -> QuerySet[Club]:
    own = _own_id(actor)
    if own is None:
        return Club.objects.none()
    joined = Membership.objects.filter(club=OuterRef("pk"), user_id=own,
                                       status=sm.CONFIRMED)
    return Club.objects.filter(Exists(joined), status=sm.CONFIRMED)


def councillor_clubs(actor) -> QuerySet[Club]:
    """BR-GYM-021: clubs the actor is the assigned Club Faculty Councillor of."""
    own = _own_id(actor)
    if own is None:
        return Club.objects.none()
    return Club.objects.filter(faculty_councillor_user_id=own)


def clubs_for(actor) -> QuerySet[Club]:
    """Student Admin sees every club; everyone else only confirmed ones (BR-GYM-007)."""
    if is_student_admin(actor):
        return Club.objects.all()
    return Club.objects.filter(status=sm.CONFIRMED)


def memberships_for(actor) -> QuerySet[Membership]:
    """AFR-GYM-020: one's own applications, plus every application to a club one leads."""
    own = _own_id(actor)
    if own is None:
        return Membership.objects.none()
    return (Membership.objects.select_related("club")
            .filter(Q(user_id=own) | Q(club__in=led_clubs(actor))))


def bookings_for(actor) -> QuerySet[Booking]:
    """Leaders and confirmed members of the booking's club only."""
    return (Booking.objects.select_related("club")
            .filter(Q(club__in=led_clubs(actor)) | Q(club__in=member_clubs(actor))))


def polls_managed_by(actor) -> QuerySet[Poll]:
    return Poll.objects.select_related("club").filter(club__in=led_clubs(actor))


def polls_targeting(batch_year: int | None, discipline: str) -> QuerySet[Poll]:
    """BR-GYM-013: polls whose audience includes this batch and branch, before the expiry check."""
    if batch_year is None:
        return Poll.objects.none()
    branch = (discipline or "").strip()
    match = Q(targets__batch_year=batch_year) & (
        Q(targets__discipline="")
        | (Q(targets__discipline__iexact=branch) if branch else Q(pk__in=[])))
    return (Poll.objects.select_related("club")
            .filter(match, club__status=sm.CONFIRMED).distinct())


def budget_requests_for(actor) -> QuerySet[BudgetRequest]:
    return (BudgetRequest.objects.select_related("club")
            .filter(club__in=led_clubs(actor)))


def reports_for(actor) -> QuerySet[EventReport]:
    """CFR-GYM-007: the submitting club's leaders and that club's assigned councillor only."""
    reach = Q(pk__in=[])
    if _has(actor, P_REPORT_VIEW):
        reach |= Q(club__in=led_clubs(actor))
    if _has(actor, P_REPORT_REVIEW):
        reach |= Q(club__in=councillor_clubs(actor))
    return EventReport.objects.select_related("club").filter(reach)
