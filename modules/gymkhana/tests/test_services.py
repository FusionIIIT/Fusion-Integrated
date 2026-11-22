from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.directory.models import UserRef
from modules.gymkhana.domain.constants import STATUS_CONFIRMED, STATUS_OPEN
from modules.gymkhana.models.club import ClubLeadership
from modules.gymkhana.services.bookings import book_event, book_session
from modules.gymkhana.services.budgets import submit_budget_request
from modules.gymkhana.services.clubs import confirm_club, create_club
from modules.gymkhana.services.leadership import change_leadership
from modules.gymkhana.services.memberships import apply_membership, approve_membership
from modules.gymkhana.services.polls import cast_vote, create_poll
from modules.gymkhana.services.reports import submit_event_report

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded_users():
    s1 = UserRef.objects.create(user_id=101, username="s101", display_name="Student 1", kind="student")
    s2 = UserRef.objects.create(user_id=102, username="s102", display_name="Student 2", kind="student")
    s3 = UserRef.objects.create(user_id=103, username="s103", display_name="Student 3", kind="student")
    f1 = UserRef.objects.create(user_id=201, username="f201", display_name="Faculty 1", kind="faculty")
    return s1, s2, s3, f1


def test_create_and_confirm_club(seeded_users):
    club = create_club(
        name="Robotics Club",
        category="Technical",
        description="Build robots",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
    )
    assert club.status == STATUS_OPEN
    assert ClubLeadership.objects.filter(club=club, is_current=True).count() == 2

    # Duplicate name conflict
    with pytest.raises(ConflictError):
        create_club(
            name="Robotics Club",
            category="Technical",
            description="Duplicate",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=201,
        )

    # Confirm club
    confirmed = confirm_club(club.id)
    assert confirmed.status == STATUS_CONFIRMED


def test_change_leadership(seeded_users):
    club = create_club(
        name="Coding Club",
        category="Technical",
        description="Coding",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
    )

    # Non-leader cannot change leadership
    with pytest.raises(PermissionDeniedError):
        change_leadership(
            club_id=club.id,
            acting_user_id=103,
            new_coordinator_id=102,
            new_co_coordinator_id=103,
        )

    # Leader can change leadership
    change_leadership(
        club_id=club.id,
        acting_user_id=101,
        new_coordinator_id=102,
        new_co_coordinator_id=103,
    )
    active_leaders = set(
        ClubLeadership.objects.filter(club=club, is_current=True).values_list("student_id", flat=True)
    )
    assert active_leaders == {102, 103}


def test_session_and_event_booking_venue_conflict(seeded_users):
    club = create_club(
        name="Dance Club",
        category="Cultural",
        description="Dance",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
    )
    confirm_club(club.id)

    today = date.today()
    book_session(
        club_id=club.id,
        acting_user_id=101,
        title="Weekly Practice",
        venue="CC1",
        booking_date=today,
        start_time=time(16, 0),
        end_time=time(18, 0),
    )

    # Overlapping session booking in same venue
    with pytest.raises(ConflictError):
        book_session(
            club_id=club.id,
            acting_user_id=101,
            title="Overlap Session",
            venue="CC1",
            booking_date=today,
            start_time=time(17, 0),
            end_time=time(19, 0),
        )

    # Cross-type overlap (event vs session) in same venue
    with pytest.raises(ConflictError):
        book_event(
            club_id=club.id,
            acting_user_id=101,
            title="Dance Fest",
            venue="CC1",
            booking_date=today,
            start_time=time(15, 0),
            end_time=time(17, 0),
        )


def test_membership_lifecycle(seeded_users):
    club = create_club(
        name="Drama Club",
        category="Cultural",
        description="Drama",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
    )

    # Cannot apply to unconfirmed club
    with pytest.raises(ConflictError):
        apply_membership(club_id=club.id, student_id=103)

    confirm_club(club.id)

    mem = apply_membership(club_id=club.id, student_id=103, remarks="Passionate actor")
    assert mem.status == STATUS_OPEN

    # Duplicate application rejected
    with pytest.raises(ConflictError):
        apply_membership(club_id=club.id, student_id=103)

    # Approve membership
    approved = approve_membership(membership_id=mem.id, acting_user_id=101)
    assert approved.status == STATUS_CONFIRMED
    assert approved.confirmed_at is not None


def test_voting_poll_lifecycle(seeded_users):
    club = create_club(
        name="Music Club",
        category="Cultural",
        description="Music",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
    )
    confirm_club(club.id)

    expires = timezone.now() + timedelta(days=2)
    poll = create_poll(
        club_id=club.id,
        acting_user_id=101,
        title="Theme for Concert",
        description="Vote for theme",
        target_batches=[],
        target_branches=[],
        expires_at=expires,
        choices=["Rock", "Classical", "Jazz"],
    )

    choice = poll.choices.first()
    cast_vote(poll_id=poll.id, student_id=103, choice_id=choice.id)
    choice.refresh_from_db()
    assert choice.votes_count == 1

    # Duplicate vote refused
    with pytest.raises(ConflictError):
        cast_vote(poll_id=poll.id, student_id=103, choice_id=choice.id)


def test_budget_and_report_submissions(seeded_users):
    club = create_club(
        name="Astronomy Club",
        category="Technical",
        description="Stars",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
    )
    confirm_club(club.id)

    file_content = b"Mock invoice"
    dummy_file = SimpleUploadedFile("invoice.pdf", file_content, content_type="application/pdf")

    # Negative budget refused
    with pytest.raises(BadRequestError):
        submit_budget_request(
            club_id=club.id,
            acting_user_id=101,
            amount=Decimal("-500"),
            purpose="Telescope",
            description="Buy telescope",
            supporting_file=dummy_file,
        )

    budget = submit_budget_request(
        club_id=club.id,
        acting_user_id=101,
        amount=Decimal("5000.00"),
        purpose="Telescope",
        description="Buy telescope",
        supporting_file=dummy_file,
    )
    assert budget.status == "open"
    assert budget.amount == Decimal("5000.00")

    report_file = SimpleUploadedFile("report.pdf", b"Event details", content_type="application/pdf")
    report = submit_event_report(
        club_id=club.id,
        acting_user_id=101,
        title="Stargazing Night Report",
        description="Successful event",
        report_file=report_file,
    )
    assert report.id is not None
