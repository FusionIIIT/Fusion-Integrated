"""Selector and scoping layer tests for Gymkhana."""

import datetime
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.api.exceptions import NotFoundError
from modules.gymkhana.domain.constants import (
    BOOKING_TYPE_SESSION,
    CLUB_STATUS_CONFIRMED,
    CLUB_STATUS_OPEN,
    POLL_STATUS_ACTIVE,
)
from modules.gymkhana.models.booking import VenueBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadershipHistory
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import Poll, PollChoice, PollTargetGroup, PollVote
from modules.gymkhana.models.report import ClubEventReport
from modules.gymkhana.selectors.bookings import (
    check_venue_conflict,
    get_booking_by_id,
    list_bookings,
)
from modules.gymkhana.selectors.budgets import get_budget_by_id
from modules.gymkhana.selectors.clubs import (
    get_club_by_id,
    get_clubs_by_ids,
    get_leadership_history,
)
from modules.gymkhana.selectors.memberships import (
    get_membership_by_id,
    student_has_membership,
)
from modules.gymkhana.selectors.polls import (
    get_poll_by_id,
    is_student_targeted,
    list_active_polls_for_student,
    student_has_voted,
)
from modules.gymkhana.selectors.reports import get_event_report_by_id
from modules.gymkhana.selectors.scoping import (
    is_club_head,
    is_faculty_councillor,
    is_student_admin,
    scope_budget_requests,
    scope_clubs,
    scope_event_reports,
    scope_memberships,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def sample_club():
    return Club.objects.create(
        name="Coding Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status=CLUB_STATUS_CONFIRMED,
    )


def test_club_selectors(sample_club):
    # get_club_by_id
    assert get_club_by_id(sample_club.id).id == sample_club.id
    with pytest.raises(NotFoundError):
        get_club_by_id(999999)

    # get_clubs_by_ids
    clubs = get_clubs_by_ids([sample_club.id])
    assert clubs.count() == 1

    # get_leadership_history
    ClubLeadershipHistory.objects.create(
        club=sample_club,
        coordinator_id=103,
        co_coordinator_id=104,
        changed_by_id=101,
    )
    history = get_leadership_history(sample_club.id)
    assert history.count() == 1


def test_booking_selectors(sample_club):
    b = VenueBooking.objects.create(
        club=sample_club,
        booking_type=BOOKING_TYPE_SESSION,
        venue="L-101",
        booking_date=datetime.date(2026, 12, 1),
        start_time=datetime.time(10, 0),
        end_time=datetime.time(12, 0),
        description="Coding Meet",
        booked_by_id=101,
    )

    # get_booking_by_id
    assert get_booking_by_id(b.id).id == b.id
    with pytest.raises(NotFoundError):
        get_booking_by_id(999999)

    # list_bookings filters
    assert list_bookings(venue="L-101").count() == 1
    assert list_bookings(venue="Hall 2").count() == 0
    assert list_bookings(booking_date=datetime.date(2026, 12, 1)).count() == 1
    assert list_bookings(club_id=sample_club.id).count() == 1

    # check_venue_conflict
    assert check_venue_conflict(
        "L-101", datetime.date(2026, 12, 1), datetime.time(11, 0), datetime.time(13, 0)
    )
    assert not check_venue_conflict(
        "L-101", datetime.date(2026, 12, 1), datetime.time(12, 0), datetime.time(14, 0)
    )
    # exclude_booking_id
    assert not check_venue_conflict(
        "L-101",
        datetime.date(2026, 12, 1),
        datetime.time(10, 0),
        datetime.time(12, 0),
        exclude_booking_id=b.id,
    )


def test_membership_selectors(sample_club):
    mem = ClubMembership.objects.create(
        club=sample_club,
        student_id=301,
        status="open",
        description="Want to learn",
    )

    # get_membership_by_id
    assert get_membership_by_id(mem.id).id == mem.id
    with pytest.raises(NotFoundError):
        get_membership_by_id(999999)

    # student_has_membership
    assert student_has_membership(sample_club.id, 301)
    assert not student_has_membership(sample_club.id, 999)


def test_poll_selectors(sample_club):
    future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)
    poll = Poll.objects.create(
        club=sample_club,
        created_by_id=101,
        title="Hackathon Theme",
        description="Vote",
        expires_at=future,
        status=POLL_STATUS_ACTIVE,
    )
    c1 = PollChoice.objects.create(poll=poll, choice_text="Web3")
    PollChoice.objects.create(poll=poll, choice_text="AI/ML")
    PollTargetGroup.objects.create(poll=poll, batch="2024", branch="CSE")

    # get_poll_by_id
    assert get_poll_by_id(poll.id).id == poll.id
    with pytest.raises(NotFoundError):
        get_poll_by_id(999999)

    # student_has_voted
    assert not student_has_voted(poll.id, 401)
    PollVote.objects.create(poll=poll, student_id=401, choice=c1)
    assert student_has_voted(poll.id, 401)

    # is_student_targeted
    assert is_student_targeted(poll, "2024", "CSE")
    assert not is_student_targeted(poll, "2023", "CSE")
    assert not is_student_targeted(poll, "2024", "ECE")

    # Poll with no targets allows all
    p_open = Poll.objects.create(
        club=sample_club,
        created_by_id=101,
        title="Open Poll",
        expires_at=future,
        status=POLL_STATUS_ACTIVE,
    )
    assert is_student_targeted(p_open, "2022", "ME")

    # Target with "all" batch/branch
    PollTargetGroup.objects.create(poll=p_open, batch="all", branch="all")
    assert is_student_targeted(p_open, "2025", "ECE")

    # list_active_polls_for_student
    assert list(list_active_polls_for_student()) == [p_open]
    targeted = list_active_polls_for_student(batch="2024", branch="CSE")
    assert poll in targeted


def test_budget_and_report_selectors(sample_club):
    dummy_file = SimpleUploadedFile("rec.pdf", b"content", content_type="application/pdf")
    b_req = ClubBudgetRequest.objects.create(
        club=sample_club,
        submitted_by_id=101,
        amount=Decimal("500.00"),
        purpose="Supplies",
        supporting_file=dummy_file,
    )
    assert get_budget_by_id(b_req.id).id == b_req.id
    with pytest.raises(NotFoundError):
        get_budget_by_id(999999)

    rep = ClubEventReport.objects.create(
        club=sample_club,
        submitted_by_id=101,
        student_incharge_id=102,
        event_name="Workshop",
        event_date=datetime.datetime.now(datetime.UTC),
        description="Great turnup",
        report_file=dummy_file,
    )
    assert get_event_report_by_id(rep.id).id == rep.id
    with pytest.raises(NotFoundError):
        get_event_report_by_id(999999)


def test_scoping_helpers(sample_club):
    # is_club_head
    assert is_club_head(101, sample_club)
    assert is_club_head(102, sample_club)
    assert not is_club_head(999, sample_club)

    # is_faculty_councillor
    assert is_faculty_councillor(201, sample_club)
    assert not is_faculty_councillor(999, sample_club)

    # is_student_admin
    assert is_student_admin(["student_admin", "student"])
    assert not is_student_admin(["student"])

    # scope_clubs
    open_club = Club.objects.create(
        name="Music Club",
        category="cultural",
        coordinator_id=501,
        co_coordinator_id=502,
        faculty_councillor_id=201,
        status=CLUB_STATUS_OPEN,
    )
    # Admin sees all
    admin_clubs = scope_clubs(user_id=999, roles=["student_admin"])
    assert sample_club in admin_clubs
    assert open_club in admin_clubs

    # Normal student sees confirmed + own open club
    stu_clubs = scope_clubs(user_id=501, roles=["student"])
    assert sample_club in stu_clubs
    assert open_club in stu_clubs

    stranger_clubs = scope_clubs(user_id=999, roles=["student"])
    assert sample_club in stranger_clubs
    assert open_club not in stranger_clubs


def test_scoping_memberships(sample_club):
    mem1 = ClubMembership.objects.create(club=sample_club, student_id=301, status="open")
    ClubMembership.objects.create(club=sample_club, student_id=302, status="confirmed")

    # Club head views all memberships for club
    head_mems = scope_memberships(user_id=101, roles=["student"], club_id=sample_club.id)
    assert head_mems.count() == 2

    # Admin views all memberships for club
    admin_mems = scope_memberships(user_id=999, roles=["student_admin"], club_id=sample_club.id)
    assert admin_mems.count() == 2

    # Plain student sees only their own
    plain_mems = scope_memberships(user_id=301, roles=["student"])
    assert plain_mems.count() == 1
    assert plain_mems.first().id == mem1.id


def test_scoping_budgets_and_reports(sample_club):
    dummy_file = SimpleUploadedFile("f.pdf", b"test", content_type="application/pdf")
    ClubBudgetRequest.objects.create(
        club=sample_club,
        submitted_by_id=101,
        amount=Decimal("100"),
        purpose="P",
        supporting_file=dummy_file,
    )
    ClubEventReport.objects.create(
        club=sample_club,
        submitted_by_id=101,
        student_incharge_id=102,
        event_name="E",
        event_date=datetime.datetime.now(datetime.UTC),
        description="D",
        report_file=dummy_file,
    )

    # Budget scoping
    # Student admin
    assert scope_budget_requests(999, ["student_admin"]).count() == 1
    assert scope_budget_requests(999, ["student_admin"], club_id=sample_club.id).count() == 1
    # Club head
    assert scope_budget_requests(101, ["student"], club_id=sample_club.id).count() == 1
    assert scope_budget_requests(101, ["student"]).count() == 1
    # Unauthorized
    with pytest.raises(NotFoundError):
        scope_budget_requests(999, ["student"], club_id=sample_club.id)

    # Event report scoping
    # CFR-GYM-007: only the assigned Club Faculty Councillor
    assert scope_event_reports(201, club_id=sample_club.id).count() == 1
    assert scope_event_reports(201).count() == 1
    for outsider in (999, 101):
        assert scope_event_reports(outsider).count() == 0
        with pytest.raises(NotFoundError):
            scope_event_reports(outsider, club_id=sample_club.id)
    with pytest.raises(NotFoundError):
        scope_event_reports(201, club_id=999999)
