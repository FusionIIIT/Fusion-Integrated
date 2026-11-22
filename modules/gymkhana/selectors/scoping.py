"""Object-level scoping selectors (BR-GYM-010, BR-GYM-021)."""
from __future__ import annotations

from django.db.models import QuerySet
from django.http import Http404

from modules.directory import contracts as directory
from modules.gymkhana.domain.polls import is_student_targeted
from modules.gymkhana.models import (
    Booking,
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubMembership,
    Poll,
)


def get_managed_club(club_id: int, actor_user_id: int) -> Club:
    """Fetch club if actor is coordinator or co-coordinator; raise 404 otherwise (BR-GYM-010)."""
    try:
        club = Club.objects.get(pk=club_id)
    except Club.DoesNotExist as exc:
        raise Http404("Club not found.") from exc

    if actor_user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise Http404("Club not found.")
    return club


def visible_clubs(actor) -> QuerySet[Club]:
    """Visible clubs: Student Admin sees all; students/public see confirmed clubs."""
    perms = getattr(actor, "permissions", frozenset())
    if "gymkhana.club.approve" in perms:
        return Club.objects.all()
    return Club.objects.filter(status="confirmed")


def visible_memberships(actor, club_id: int | None = None) -> QuerySet[ClubMembership]:
    """Visible memberships: Students see their own; Club Head sees their club's applications."""
    qs = ClubMembership.objects.select_related("club")
    if club_id is not None:
        get_managed_club(club_id, actor.user_id)
        return qs.filter(club_id=club_id)
    return qs.filter(student_id=actor.user_id)


def visible_bookings(actor=None) -> QuerySet[Booking]:
    """Public calendar schedule of sessions and events."""
    return Booking.objects.select_related("club").order_by("date", "start_time")


def visible_polls(actor) -> QuerySet[Poll]:
    """Visible polls: active unexpired polls where student matches target audience."""
    from django.utils import timezone

    now = timezone.now()
    active_polls = (
        Poll.objects.filter(status="active", expires_at__gt=now).prefetch_related("targets")
    )

    student_batch = getattr(actor, "batch_year", None)
    student_disc = getattr(actor, "discipline", "")
    if student_batch is None:
        user_info = directory.get_users([actor.user_id]).get(actor.user_id)
        if user_info:
            student_batch = user_info.batch_year
            student_disc = user_info.discipline

    eligible_pks = []
    for poll in active_polls:
        targets = list(poll.targets.values("batch_year", "discipline"))
        if is_student_targeted(student_batch, student_disc, targets):
            eligible_pks.append(poll.pk)

    return Poll.objects.filter(pk__in=eligible_pks)


def visible_budget_requests(actor, club_id: int) -> QuerySet[ClubBudgetRequest]:
    """Budget requests for actor's managed club."""
    get_managed_club(club_id, actor.user_id)
    return ClubBudgetRequest.objects.filter(club_id=club_id)


def visible_event_reports(
    actor,
    report_id: int | None = None,
    club_id: int | None = None,
) -> QuerySet[ClubEventReport]:
    """Filter by club__faculty_councillor_id == actor.user_id for faculty review (BR-GYM-021)."""
    qs = ClubEventReport.objects.select_related("club")
    roles = set(getattr(actor, "roles", ()))

    if "faculty" in roles:
        qs = qs.filter(club__faculty_councillor_id=actor.user_id)
        if report_id is not None:
            if not qs.filter(pk=report_id).exists():
                raise Http404("Report not found.")
            return qs.filter(pk=report_id)
        return qs

    if club_id is not None:
        get_managed_club(club_id, actor.user_id)
        return qs.filter(club_id=club_id)

    if report_id is not None:
        report = qs.filter(pk=report_id).first()
        if not report:
            raise Http404("Report not found.")
        get_managed_club(report.club_id, actor.user_id)
        return qs.filter(pk=report_id)

    return qs.none()
