from django.db.models import QuerySet

from modules.gymkhana.domain.constants import (
    ROLE_CO_COORDINATOR,
    ROLE_COORDINATOR,
    STATUS_CONFIRMED,
)
from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import VotingPoll
from modules.gymkhana.models.report import ClubEventReport


def is_club_head(user_id: int, club_id: int) -> bool:
    return ClubLeadership.objects.filter(
        club_id=club_id,
        student_id=user_id,
        role__in=[ROLE_COORDINATOR, ROLE_CO_COORDINATOR],
        is_current=True,
    ).exists()


def is_club_councillor(user_id: int, club_id: int) -> bool:
    return Club.objects.filter(id=club_id, faculty_councillor_id=user_id).exists()


def scope_clubs(user) -> QuerySet[Club]:
    # Staff/Admin or student admin can view all clubs; standard users see confirmed or their own.
    if getattr(user, "is_admin", False) or getattr(user, "is_staff", False):
        return Club.objects.all()
    user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
    if not user_id:
        return Club.objects.filter(status=STATUS_CONFIRMED)
    led_clubs = ClubLeadership.objects.filter(student_id=user_id, is_current=True).values_list(
        "club_id", flat=True
    )
    councillor_clubs = Club.objects.filter(faculty_councillor_id=user_id).values_list(
        "id", flat=True
    )
    return Club.objects.filter(id__in=set(led_clubs) | set(councillor_clubs)) | Club.objects.filter(
        status=STATUS_CONFIRMED
    )


def scope_bookings(user, club: Club) -> QuerySet[ClubBooking]:
    return ClubBooking.objects.filter(club=club)


def scope_memberships(user, club: Club) -> QuerySet[ClubMembership]:
    user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
    if is_club_head(user_id, club.id) or getattr(user, "is_admin", False):
        return ClubMembership.objects.filter(club=club)
    return ClubMembership.objects.filter(club=club, student_id=user_id)


def scope_polls(user) -> QuerySet[VotingPoll]:
    return VotingPoll.objects.all()


def scope_budgets(user, club: Club) -> QuerySet[ClubBudgetRequest]:
    user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
    if is_club_head(user_id, club.id) or getattr(user, "is_admin", False):
        return ClubBudgetRequest.objects.filter(club=club)
    return ClubBudgetRequest.objects.none()


def scope_reports(user, club: Club) -> QuerySet[ClubEventReport]:
    user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
    is_head = is_club_head(user_id, club.id)
    is_councillor = is_club_councillor(user_id, club.id)
    if is_councillor or is_head or getattr(user, "is_admin", False):
        return ClubEventReport.objects.filter(club=club)
    return ClubEventReport.objects.none()
