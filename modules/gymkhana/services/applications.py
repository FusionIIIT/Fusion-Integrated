"""
Workflow and application service functions for gymkhana.
"""

from datetime import date, datetime, time
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from modules.gymkhana.domain.policy import (
    validate_student_leadership,
    validate_faculty_councillor,
    validate_club_category,
    validate_club_confirmation_transition,
    validate_booking_time_range,
    check_cross_type_venue_conflict,
    validate_membership_application,
    validate_club_head_authorization,
    validate_membership_approval_transition,
    validate_poll_creation,
    validate_vote_eligibility,
    validate_budget_amount,
    validate_event_report,
    validate_configured_venue,
    validate_faculty_report_review,
    validate_leadership_succession,
    ClubStatus,
    MembershipStatus,
)
from modules.gymkhana.models import (
    Club,
    ClubLeadership,
    ClubMembership,
    VenueBooking,
    VotingPoll,
    PollOption,
    PollVote,
    ClubBudgetRequest,
    ClubEventReport,
)


@transaction.atomic
def create_club(
    *,
    name: str,
    category: str,
    coordinator_id: int,
    co_coordinator_id: int,
    faculty_councillor_id: int,
    description: str = "",
) -> Club:
    """
    UC-GYM-001 / BW-GYM-03: Create a new club in 'open' status.
    """
    valid_lead, lead_err = validate_student_leadership(coordinator_id, co_coordinator_id)
    if not valid_lead:
        raise ValueError(lead_err)

    valid_fac, fac_err = validate_faculty_councillor(faculty_councillor_id)
    if not valid_fac:
        raise ValueError(fac_err)

    valid_cat, cat_err = validate_club_category(category)
    if not valid_cat:
        raise ValueError(cat_err)

    club = Club.objects.create(
        name=name,
        category=category,
        description=description,
        status=ClubStatus.OPEN.value,
    )

    ClubLeadership.objects.create(
        club=club,
        coordinator_id=coordinator_id,
        co_coordinator_id=co_coordinator_id,
        faculty_councillor_id=faculty_councillor_id,
        is_active=True,
    )

    return club


@transaction.atomic
def confirm_club(*, club_id: int) -> Club:
    """
    UC-GYM-011 / BW-GYM-03: Student Admin confirms an open club.
    """
    club = Club.objects.select_for_update().get(id=club_id)
    valid_trans, trans_err = validate_club_confirmation_transition(club.status)
    if not valid_trans:
        raise ValueError(trans_err)

    club.status = ClubStatus.CONFIRMED.value
    club.save(update_fields=["status", "updated_at"])
    return club


@transaction.atomic
def change_club_leadership(
    *,
    club_id: int,
    actor_id: int,
    new_coordinator_id: int,
    new_co_coordinator_id: int,
) -> ClubLeadership:
    """
    UC-GYM-008: Change club coordinator and co-coordinator.
    Superseded active leadership assignments must no longer remain current (BR-GYM-016).
    """
    club = Club.objects.get(id=club_id)
    active_leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()
    if not active_leadership:
        raise ValueError("No active leadership record found for this club.")

    if not validate_club_head_authorization(
        actor_id, active_leadership.coordinator_id, active_leadership.co_coordinator_id
    ):
        raise PermissionError("Only current active club coordinators may change leadership.")

    valid_lead, lead_err = validate_student_leadership(new_coordinator_id, new_co_coordinator_id)
    if not valid_lead:
        raise ValueError(lead_err)

    # Deactivate current active leadership
    ClubLeadership.objects.filter(club=club, is_active=True).update(is_active=False)

    # Create new active leadership
    new_leadership = ClubLeadership.objects.create(
        club=club,
        coordinator_id=new_coordinator_id,
        co_coordinator_id=new_co_coordinator_id,
        faculty_councillor_id=active_leadership.faculty_councillor_id,
        is_active=True,
    )

    return new_leadership


@transaction.atomic
def book_venue(
    *,
    club_id: int,
    actor_id: int,
    booking_type: str,
    venue_name: str,
    booking_date: date,
    start_time: time,
    end_time: time,
    description: str = "",
    poster_url: str = "",
) -> VenueBooking:
    """
    UC-GYM-002, UC-GYM-003: Book a venue for session or event.
    Enforces time range (BR-GYM-005) and cross-type exclusivity (BR-GYM-006).
    """
    club = Club.objects.get(id=club_id)
    active_leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()
    if not active_leadership or not validate_club_head_authorization(
        actor_id, active_leadership.coordinator_id, active_leadership.co_coordinator_id
    ):
        raise PermissionError("Only active club coordinators may book venues.")

    valid_venue, venue_err = validate_configured_venue(venue_name)
    if not valid_venue:
        raise ValueError(venue_err)

    valid_time, time_err = validate_booking_time_range(start_time, end_time)
    if not valid_time:
        raise ValueError(time_err)

    # Query existing bookings on that date and venue
    existing_bookings = VenueBooking.objects.filter(
        venue_name=venue_name,
        booking_date=booking_date,
    ).values_list("start_time", "end_time")

    if check_cross_type_venue_conflict(list(existing_bookings), start_time, end_time):
        raise ValueError(f"Venue '{venue_name}' is already booked during this time on {booking_date}.")

    booking = VenueBooking.objects.create(
        club=club,
        booking_type=booking_type,
        venue_name=venue_name,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        poster_url=poster_url,
        created_by_id=actor_id,
    )
    return booking


@transaction.atomic
def apply_club_membership(
    *,
    club_id: int,
    student_id: int,
) -> ClubMembership:
    """
    UC-GYM-004 / BW-GYM-01: Student applies for club membership.
    Club must be confirmed; no duplicate application (BR-GYM-007, BR-GYM-009).
    """
    club = Club.objects.get(id=club_id)
    has_existing = ClubMembership.objects.filter(club=club, student_id=student_id).exists()

    valid_app, app_err = validate_membership_application(club.status, has_existing)
    if not valid_app:
        raise ValueError(app_err)

    membership = ClubMembership.objects.create(
        club=club,
        student_id=student_id,
        status=MembershipStatus.OPEN.value,
    )
    return membership


@transaction.atomic
def approve_club_membership(
    *,
    membership_id: int,
    actor_id: int,
) -> ClubMembership:
    """
    UC-GYM-005 / BW-GYM-01: Club Head approves open membership.
    """
    membership = ClubMembership.objects.select_for_update().get(id=membership_id)
    club = membership.club
    active_leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()

    if not active_leadership or not validate_club_head_authorization(
        actor_id, active_leadership.coordinator_id, active_leadership.co_coordinator_id
    ):
        raise PermissionError("Only active club coordinators may approve membership applications.")

    valid_trans, trans_err = validate_membership_approval_transition(membership.status)
    if not valid_trans:
        raise ValueError(trans_err)

    membership.status = MembershipStatus.CONFIRMED.value
    membership.confirmed_at = timezone.now()
    membership.save(update_fields=["status", "confirmed_at"])
    return membership


@transaction.atomic
def create_voting_poll(
    *,
    club_id: int,
    actor_id: int,
    title: str,
    options: list[str],
    expires_at: datetime,
    description: str = "",
    target_batch: str = "ALL",
    target_branch: str = "ALL",
) -> VotingPoll:
    """
    UC-GYM-006 / BW-GYM-02: Create voting poll with >= 2 options.
    """
    club = Club.objects.get(id=club_id)
    active_leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()
    if not active_leadership or not validate_club_head_authorization(
        actor_id, active_leadership.coordinator_id, active_leadership.co_coordinator_id
    ):
        raise PermissionError("Only active club coordinators may create polls.")

    valid_poll, poll_err = validate_poll_creation(len(options), target_batch, target_branch)
    if not valid_poll:
        raise ValueError(poll_err)

    poll = VotingPoll.objects.create(
        club=club,
        title=title,
        description=description,
        target_batch=target_batch,
        target_branch=target_branch,
        is_active=True,
        expires_at=expires_at,
        created_by_id=actor_id,
    )

    for opt_text in options:
        PollOption.objects.create(poll=poll, option_text=opt_text)

    return poll


@transaction.atomic
def cast_poll_vote(
    *,
    poll_id: int,
    student_id: int,
    option_id: int,
    student_batch: str,
    student_branch: str,
    current_time: datetime | None = None,
) -> PollVote:
    """
    UC-GYM-007 / BW-GYM-02: Cast single vote in active poll.
    """
    if current_time is None:
        current_time = timezone.now()

    poll = VotingPoll.objects.get(id=poll_id)
    option = PollOption.objects.get(id=option_id, poll=poll)
    already_voted = PollVote.objects.filter(poll=poll, student_id=student_id).exists()

    valid_vote, vote_err = validate_vote_eligibility(
        poll_is_active=poll.is_active,
        expires_at=poll.expires_at,
        current_time=current_time,
        student_batch=student_batch,
        student_branch=student_branch,
        target_batch=poll.target_batch,
        target_branch=poll.target_branch,
        already_voted=already_voted,
    )
    if not valid_vote:
        raise ValueError(vote_err)

    vote = PollVote.objects.create(
        poll=poll,
        option=option,
        student_id=student_id,
    )
    return vote


@transaction.atomic
def submit_budget_request(
    *,
    club_id: int,
    actor_id: int,
    requested_amount: Decimal | float,
    description: str,
    supporting_file: str,
) -> ClubBudgetRequest:
    """
    UC-GYM-009: Submit club budget request (amount >= 0, supporting file required).
    """
    club = Club.objects.get(id=club_id)
    active_leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()
    if not active_leadership or not validate_club_head_authorization(
        actor_id, active_leadership.coordinator_id, active_leadership.co_coordinator_id
    ):
        raise PermissionError("Only active club coordinators may submit budget requests.")

    valid_amt, amt_err = validate_budget_amount(requested_amount, bool(supporting_file))
    if not valid_amt:
        raise ValueError(amt_err)

    req = ClubBudgetRequest.objects.create(
        club=club,
        requested_amount=requested_amount,
        description=description,
        supporting_file=supporting_file,
        status="open",
        submitted_by_id=actor_id,
    )
    return req


@transaction.atomic
def submit_event_report(
    *,
    club_id: int,
    actor_id: int,
    event_name: str,
    event_date: date,
    report_file: str,
) -> ClubEventReport:
    """
    UC-GYM-010: Submit club event report (report file required).
    """
    club = Club.objects.get(id=club_id)
    active_leadership = ClubLeadership.objects.filter(club=club, is_active=True).first()
    if not active_leadership or not validate_club_head_authorization(
        actor_id, active_leadership.coordinator_id, active_leadership.co_coordinator_id
    ):
        raise PermissionError("Only active club coordinators may submit event reports.")

    valid_rep, rep_err = validate_event_report(bool(report_file))
    if not valid_rep:
        raise ValueError(rep_err)

    report = ClubEventReport.objects.create(
        club=club,
        event_name=event_name,
        event_date=event_date,
        report_file=report_file,
        submitted_by_id=actor_id,
    )
    return report


def review_event_report(
    *,
    report_id: int,
    faculty_id: int,
) -> ClubEventReport:
    """
    UC-GYM-012: Assigned Club Faculty Councillor reviews event report.
    """
    report = ClubEventReport.objects.get(id=report_id)
    leadership = ClubLeadership.objects.filter(club=report.club, is_active=True).first()
    if not leadership:
        raise ValueError("No active leadership found for this club.")

    if not validate_faculty_report_review(faculty_id, leadership.faculty_councillor_id):
        raise PermissionError("Only the assigned Club Faculty Councillor may review event reports.")

    return report
