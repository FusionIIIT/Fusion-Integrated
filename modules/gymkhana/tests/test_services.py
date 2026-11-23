"""Service layer tests verifying business rules for Gymkhana."""

import datetime
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadershipHistory
from modules.gymkhana.services.bookings import book_event, book_session
from modules.gymkhana.services.budgets import submit_budget_request
from modules.gymkhana.services.clubs import (
    approve_club,
    change_leadership,
    create_club,
)
from modules.gymkhana.services.memberships import apply_membership, approve_membership
from modules.gymkhana.services.polls import cast_vote, create_poll
from modules.gymkhana.services.reports import submit_event_report

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def directory_users():
    # Student leaders
    UserRef.objects.create(
        user_id=101, username="stu101", display_name="Student 101", kind="student", is_active=True
    )
    UserRef.objects.create(
        user_id=102, username="stu102", display_name="Student 102", kind="student", is_active=True
    )
    UserRef.objects.create(
        user_id=103, username="stu103", display_name="Student 103", kind="student", is_active=True
    )
    UserRef.objects.create(
        user_id=104, username="stu104", display_name="Student 104", kind="student", is_active=True
    )
    # Faculty councillor
    UserRef.objects.create(
        user_id=201, username="fac201", display_name="Faculty 201", kind="faculty", is_active=True
    )
    # Non-student/faculty staff
    UserRef.objects.create(
        user_id=301, username="stf301", display_name="Staff 301", kind="staff", is_active=True
    )


def test_club_creation_and_approval_workflow(directory_users):
    # AFR-GYM-001 to 006, BW-GYM-03
    club = create_club(
        name="Astronomy Club",
        category="Technical",
        description="Stargazing and telescopes",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        creator_id=999,
    )
    assert club.status == "open"
    assert club.category == "technical"

    # Only Student Admin can approve (AFR-GYM-006, BW-GYM-03)
    with pytest.raises(PermissionDeniedError):
        approve_club(club_id=club.id, approver_id=101, roles=["student"])

    confirmed_club = approve_club(club_id=club.id, approver_id=999, roles=["student_admin"])
    assert confirmed_club.status == "confirmed"


def test_club_creation_rejects_invalid_roles(directory_users):
    # BR-GYM-001: coordinator must be student
    with pytest.raises(BadRequestError):
        create_club(
            name="Invalid Club 1",
            category="Technical",
            description="",
            coordinator_id=301,  # staff, not student
            co_coordinator_id=102,
            faculty_councillor_id=201,
            creator_id=999,
        )

    # BR-GYM-002: councillor must be faculty
    with pytest.raises(BadRequestError):
        create_club(
            name="Invalid Club 2",
            category="Technical",
            description="",
            coordinator_id=101,
            co_coordinator_id=102,
            faculty_councillor_id=103,  # student, not faculty
            creator_id=999,
        )


def test_leadership_succession(directory_users):
    # UC-GYM-008, AFR-GYM-007 to 009, BR-GYM-016
    club = Club.objects.create(
        name="Robotics Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )

    # Non-club head cannot change leadership
    with pytest.raises(PermissionDeniedError):
        change_leadership(
            club_id=club.id,
            actor_id=103,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )

    updated = change_leadership(
        club_id=club.id,
        actor_id=101,
        new_coordinator_id=103,
        new_co_coordinator_id=104,
    )
    assert updated.coordinator_id == 103
    assert updated.co_coordinator_id == 104
    assert ClubLeadershipHistory.objects.filter(club=club, coordinator_id=103).exists()


def test_cross_type_venue_exclusivity(directory_users):
    # BR-GYM-006: Session and Event bookings conflict across same venue and date
    club = Club.objects.create(
        name="Drama Club",
        category="cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )

    # 1. Book a session: 10:00 to 12:00 in Hall 1
    session = book_session(
        club_id=club.id,
        actor_id=101,
        venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10),
        start_time=datetime.time(10, 0),
        end_time=datetime.time(12, 0),
        description="Rehearsal",
    )
    assert session.pk is not None

    # 2. Try booking an event that overlaps: 11:30 to 13:00 in Hall 1 -> must conflict!
    with pytest.raises(ConflictError):
        book_event(
            club_id=club.id,
            actor_id=101,
            venue="Hall 1",
            booking_date=datetime.date(2026, 12, 10),
            start_time=datetime.time(11, 30),
            end_time=datetime.time(13, 0),
            name="Annual Play",
            description="",
            faculty_councillor_id=201,
        )

    # 3. Non-overlapping booking in Hall 1 on same date: 14:00 to 16:00 -> succeeds!
    event = book_event(
        club_id=club.id,
        actor_id=101,
        venue="Hall 1",
        booking_date=datetime.date(2026, 12, 10),
        start_time=datetime.time(14, 0),
        end_time=datetime.time(16, 0),
        name="Annual Play Matinee",
        description="",
        faculty_councillor_id=201,
    )
    assert event.pk is not None


def test_membership_lifecycle(directory_users):
    # BW-GYM-01: Apply -> Open -> Approve -> Confirmed
    club = Club.objects.create(
        name="Sports Club",
        category="sports",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )

    mem = apply_membership(club_id=club.id, student_id=103, description="Football player")
    assert mem.status == "open"

    # Duplicate application rejected (BR-GYM-009)
    with pytest.raises(ConflictError):
        apply_membership(club_id=club.id, student_id=103)

    # Approval by Club Head
    approved = approve_membership(membership_id=mem.id, actor_id=101, remarks="Welcome aboard")
    assert approved.status == "confirmed"
    assert approved.remarks == "Welcome aboard"


def test_poll_creation_and_voting(directory_users):
    # BW-GYM-02, BR-GYM-013, BR-GYM-015
    club = Club.objects.create(
        name="Quiz Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )

    future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3)
    poll = create_poll(
        club_id=club.id,
        actor_id=101,
        title="Weekly Quiz Topic",
        description="Choose topic",
        expires_at=future,
        choices=["Sci-Tech", "History", "Pop Culture"],
        target_groups=[("2024", "CSE")],
    )
    assert poll.choices.count() == 3

    choice_id = poll.choices.first().id

    # Ineligible student (wrong batch/branch) rejected
    with pytest.raises(PermissionDeniedError):
        cast_vote(
            poll_id=poll.id,
            student_id=103,
            choice_id=choice_id,
            student_batch="2023",
            student_branch="ECE",
        )

    # Eligible student votes
    vote = cast_vote(
        poll_id=poll.id,
        student_id=103,
        choice_id=choice_id,
        student_batch="2024",
        student_branch="CSE",
    )
    assert vote.pk is not None

    # Duplicate vote rejected (BR-GYM-015)
    with pytest.raises(ConflictError):
        cast_vote(
            poll_id=poll.id,
            student_id=103,
            choice_id=choice_id,
            student_batch="2024",
            student_branch="CSE",
        )


def test_budget_request_and_report_submissions(directory_users):
    # CFR-GYM-006, CFR-GYM-007
    club = Club.objects.create(
        name="Art Club",
        category="cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )

    dummy_file = SimpleUploadedFile(
        "bill.pdf", b"Dummy file content", content_type="application/pdf"
    )

    # Negative budget amount rejected (BR-GYM-017)
    with pytest.raises(BadRequestError):
        submit_budget_request(
            club_id=club.id,
            actor_id=101,
            amount=Decimal("-500"),
            purpose="Canvases",
            description="",
            supporting_file=dummy_file,
        )

    # Valid budget request stored in open tracking status
    budget = submit_budget_request(
        club_id=club.id,
        actor_id=101,
        amount=Decimal("1500.00"),
        purpose="Canvases",
        description="Art exhibition",
        supporting_file=dummy_file,
    )
    assert budget.status == "open"

    # Event report submission with mandatory file
    report = submit_event_report(
        club_id=club.id,
        actor_id=101,
        student_incharge_id=102,
        event_name="Art Fest 2026",
        event_date=datetime.datetime.now(datetime.UTC),
        description="Great event",
        report_file=dummy_file,
    )
    assert report.pk is not None


def test_service_error_branches(directory_users):
    from core.api.exceptions import NotFoundError
    from modules.gymkhana.tasks import expire_polls

    # 1. Club services not found / unconfirmed
    with pytest.raises(NotFoundError):
        approve_club(club_id=999999, approver_id=1, roles=["student_admin"])

    open_club = Club.objects.create(
        name="Open Test Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="open",
    )
    # Cannot change leadership if club not found or invalid leaders
    with pytest.raises(NotFoundError):
        change_leadership(
            club_id=999999,
            actor_id=101,
            new_coordinator_id=103,
            new_co_coordinator_id=104,
        )

    # Identical coordinator and co-coordinator rejected
    with pytest.raises(BadRequestError):
        change_leadership(
            club_id=open_club.id,
            actor_id=101,
            new_coordinator_id=103,
            new_co_coordinator_id=103,
        )

    # Cannot approve already confirmed club
    open_club.status = "confirmed"
    open_club.save()
    with pytest.raises(ConflictError):
        approve_club(club_id=open_club.id, approver_id=1, roles=["student_admin"])

    # 2. Bookings error branches
    with pytest.raises(NotFoundError):
        book_session(
            club_id=999999,
            actor_id=101,
            venue="L-101",
            booking_date=datetime.date(2026, 12, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            description="",
        )

    # Non-head booking session
    with pytest.raises(PermissionDeniedError):
        book_session(
            club_id=open_club.id,
            actor_id=999,
            venue="L-101",
            booking_date=datetime.date(2026, 12, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            description="",
        )

    # Event booking errors
    with pytest.raises(NotFoundError):
        book_event(
            club_id=999999,
            actor_id=101,
            venue="L-101",
            booking_date=datetime.date(2026, 12, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            name="E",
            description="",
            faculty_councillor_id=201,
        )

    with pytest.raises(PermissionDeniedError):
        book_event(
            club_id=open_club.id,
            actor_id=999,
            venue="L-101",
            booking_date=datetime.date(2026, 12, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            name="E",
            description="",
            faculty_councillor_id=201,
        )

    # Councillor must be faculty
    with pytest.raises(BadRequestError):
        book_event(
            club_id=open_club.id,
            actor_id=101,
            venue="L-101",
            booking_date=datetime.date(2026, 12, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            name="E",
            description="",
            faculty_councillor_id=102,
        )

    # 3. Membership error branches
    with pytest.raises(NotFoundError):
        apply_membership(club_id=999999, student_id=103)

    # Apply to unconfirmed club fails
    unconfirmed = Club.objects.create(
        name="Unconfirmed Club",
        category="sports",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="open",
    )
    with pytest.raises(ConflictError):
        apply_membership(club_id=unconfirmed.id, student_id=103)

    with pytest.raises(NotFoundError):
        approve_membership(membership_id=999999, actor_id=101)

    # 4. Poll error branches
    with pytest.raises(NotFoundError):
        create_poll(
            club_id=999999,
            actor_id=101,
            title="T",
            description="D",
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            choices=["A", "B"],
            target_groups=[("all", "all")],
        )

    with pytest.raises(PermissionDeniedError):
        create_poll(
            club_id=open_club.id,
            actor_id=999,
            title="T",
            description="D",
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            choices=["A", "B"],
            target_groups=[("all", "all")],
        )

    # Expire polls task
    expire_count = expire_polls()
    assert expire_count >= 0

