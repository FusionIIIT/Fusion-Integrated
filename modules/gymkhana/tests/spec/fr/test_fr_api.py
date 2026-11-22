import re
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.notification import GymkhanaNotificationOutbox
from modules.gymkhana.models.poll import PollChoice, PollVote, VotingPoll
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db

BOOKING_DATE = date(2027, 1, 15)


@pytest.fixture
def gym_context():
    students = (
        (101, "Leader", 2023, "CSE"),
        (102, "Co Leader", 2023, "CSE"),
        (103, "Student One", 2023, "CSE"),
        (104, "Student Two", 2024, "CSE"),
        (105, "Student Other Branch", 2023, "ECE"),
    )
    for user_id, name, batch_year, discipline in students:
        UserRef.objects.create(
            user_id=user_id,
            username=f"s{user_id}",
            display_name=name,
            kind="student",
            batch_year=batch_year,
            discipline=discipline,
        )
    for user_id, username, name in (
        (201, "f201", "Assigned Faculty"),
        (202, "f202", "Other Faculty"),
    ):
        UserRef.objects.create(
            user_id=user_id,
            username=username,
            display_name=name,
            kind="faculty",
        )
    return SimpleNamespace(
        club=_make_club("Test Club"),
        students={row[0] for row in students},
    )


def _make_club(name, *, status="confirmed", faculty_councillor_id=201):
    club = Club.objects.create(
        name=name,
        category="Cultural",
        description="Test club",
        faculty_councillor_id=faculty_councillor_id,
        status=status,
    )
    ClubLeadership.objects.create(
        club=club, student_id=101, role="coordinator", is_current=True
    )
    ClubLeadership.objects.create(
        club=club, student_id=102, role="co_coordinator", is_current=True
    )
    return club


def _client(stub_iam, user_id, permissions, *, kind="student", role=None):
    active_role = role or kind
    stub_iam(
        make_session(
            user_id=user_id,
            modules=("gymkhana",),
            permissions=permissions,
            kind=kind,
            roles=(active_role,),
            active_role=active_role,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def _club_create_payload(**overrides):
    payload = {
        "name": "New Club",
        "category": "Technical",
        "description": "A test club",
        "coordinator_id": 101,
        "co_coordinator_id": 102,
        "faculty_councillor_id": 201,
    }
    return payload | overrides


def _booking_payload(**overrides):
    payload = {
        "title": "Test Activity",
        "venue": "L-101",
        "date": BOOKING_DATE.isoformat(),
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "description": "Test booking",
    }
    return payload | overrides


def _book(client, club_id, booking_type, payload):
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/{booking_type}s/",
        payload,
        format="json",
    )


def _poll_payload(**overrides):
    payload = {
        "title": "Test Poll",
        "description": "Choose one",
        "target_batches": ["2023"],
        "target_branches": ["CSE"],
        "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
        "choices": ["Option A", "Option B"],
    }
    return payload | overrides


def _create_report(client, club_id, *, file=True):
    payload = {
        "title": "Annual Event",
        "description": "Event outcomes",
        "student_incharge_id": 103,
        "event_name": "Annual Event",
        "event_datetime": datetime(2027, 1, 14, 10, tzinfo=UTC).isoformat(),
    }
    if file:
        payload["report_file"] = SimpleUploadedFile(
            "report.pdf", b"%PDF-1.4 report", content_type="application/pdf"
        )
    return client.post(
        f"/api/v1/gymkhana/clubs/{club_id}/reports/submit/",
        payload,
        format="multipart",
    )


def _all_route_strings(patterns=None, prefix=""):
    patterns = get_resolver().url_patterns if patterns is None else patterns
    for pattern in patterns:
        route = f"{prefix}{pattern.pattern}"
        if isinstance(pattern, URLResolver):
            yield from _all_route_strings(pattern.url_patterns, route)
        else:
            yield route


def test_gym_afr_001(stub_iam, gym_context):
    """test_id=GYM-AFR-001; source_id=AFR-GYM-001 Club creation"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    response = admin.post(
        "/api/v1/gymkhana/clubs/", _club_create_payload(), format="json"
    )
    assert response.status_code == 201
    club_id = response.json()["id"]
    assert Club.objects.filter(
        pk=club_id,
        name="New Club",
        category="Technical",
        description="A test club",
        faculty_councillor_id=201,
    ).exists()
    assert set(
        ClubLeadership.objects.filter(club_id=club_id, is_current=True).values_list(
            "student_id", flat=True
        )
    ) == {101, 102}


def test_gym_afr_002_valid(stub_iam, gym_context):
    """test_id=GYM-AFR-002-valid; source_id=AFR-GYM-002 Valid student leaders"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Valid Leaders Club"),
        format="json",
    )
    assert response.status_code == 201
    leadership = ClubLeadership.objects.filter(
        club_id=response.json()["id"], is_current=True
    )
    assert set(leadership.values_list("student_id", flat=True)) == {101, 102}
    assert leadership.count() == 2


def test_gym_afr_002_invalid_coordinator(stub_iam, gym_context):
    """test_id=GYM-AFR-002-invalid-coordinator; source_id=AFR-GYM-002 Invalid coordinator"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    initial_count = Club.objects.count()
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Invalid Coordinator", coordinator_id=99901),
        format="json",
    )
    assert response.status_code == 422
    assert Club.objects.count() == initial_count


def test_gym_afr_002_invalid_co_coordinator(stub_iam, gym_context):
    """test_id=GYM-AFR-002-invalid-co-coordinator; source_id=AFR-GYM-002 Invalid co-coordinator"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    initial_count = Club.objects.count()
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Invalid Co Coordinator", co_coordinator_id=99902),
        format="json",
    )
    assert response.status_code == 422
    assert Club.objects.count() == initial_count


def test_gym_afr_003_valid(stub_iam, gym_context):
    """test_id=GYM-AFR-003-valid; source_id=AFR-GYM-003 Valid Club Faculty Councillor"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Faculty Assignment Club", faculty_councillor_id=201),
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["faculty_councillor_id"] == 201


def test_gym_afr_003_invalid(stub_iam, gym_context):
    """test_id=GYM-AFR-003-invalid; source_id=AFR-GYM-003 Invalid Club Faculty Councillor"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    initial_count = Club.objects.count()
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Invalid Faculty Club", faculty_councillor_id=103),
        format="json",
    )
    assert response.status_code == 422
    assert Club.objects.count() == initial_count


def test_gym_afr_004_categories(stub_iam, gym_context):
    """test_id=GYM-AFR-004-categories; source_id=AFR-GYM-004 Allowed categories"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    for category in ("Technical", "Sports", "Cultural"):
        response = admin.post(
            "/api/v1/gymkhana/clubs/",
            _club_create_payload(name=f"{category} Club", category=category),
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["category"] == category


def test_gym_afr_004_invalid(stub_iam, gym_context):
    """test_id=GYM-AFR-004-invalid; source_id=AFR-GYM-004 Prohibited category"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    initial_count = Club.objects.count()
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Unsupported Category Club", category="Academic"),
        format="json",
    )
    assert response.status_code == 422
    assert Club.objects.count() == initial_count


def test_gym_afr_005(stub_iam, gym_context):
    """test_id=GYM-AFR-005; source_id=AFR-GYM-005 Open club lifecycle"""
    admin = _client(stub_iam, 9000, ("gymkhana.club.create",), kind="staff")
    response = admin.post(
        "/api/v1/gymkhana/clubs/",
        _club_create_payload(name="Open Lifecycle Club"),
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert Club.objects.get(pk=response.json()["id"]).status == "open"


def test_gym_afr_006(stub_iam, gym_context):
    """test_id=GYM-AFR-006; source_id=AFR-GYM-006 Student Admin approval"""
    open_club = _make_club("Club Awaiting Confirmation", status="open")
    admin = _client(stub_iam, 9000, ("gymkhana.club.approve",), kind="staff")
    response = admin.post(f"/api/v1/gymkhana/clubs/{open_club.id}/confirm/")
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    open_club.refresh_from_db()
    assert open_club.status == "confirmed"


def test_gym_afr_007(stub_iam, gym_context):
    """test_id=GYM-AFR-007; source_id=AFR-GYM-007 Leadership replacement"""
    head = _client(stub_iam, 101, ("gymkhana.leadership.update",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/leadership/",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 104},
        format="json",
    )
    assert response.status_code == 200
    assert {row["student_id"] for row in response.json()["leaderships"]} == {103, 104}


def test_gym_afr_008_invalid_coordinator(stub_iam, gym_context):
    """test_id=GYM-AFR-008-invalid-coordinator; source_id=AFR-GYM-008 Invalid replacement coordinator"""
    head = _client(stub_iam, 101, ("gymkhana.leadership.update",))
    before = set(
        ClubLeadership.objects.filter(club=gym_context.club, is_current=True).values_list(
            "student_id", flat=True
        )
    )
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/leadership/",
        {"new_coordinator_id": 99903, "new_co_coordinator_id": 104},
        format="json",
    )
    assert response.status_code == 422
    assert set(
        ClubLeadership.objects.filter(club=gym_context.club, is_current=True).values_list(
            "student_id", flat=True
        )
    ) == before


def test_gym_afr_008_invalid_co_coordinator(stub_iam, gym_context):
    """test_id=GYM-AFR-008-invalid-co-coordinator; source_id=AFR-GYM-008 Invalid replacement co-coordinator"""
    head = _client(stub_iam, 101, ("gymkhana.leadership.update",))
    before = set(
        ClubLeadership.objects.filter(club=gym_context.club, is_current=True).values_list(
            "student_id", flat=True
        )
    )
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/leadership/",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 99904},
        format="json",
    )
    assert response.status_code == 422
    assert set(
        ClubLeadership.objects.filter(club=gym_context.club, is_current=True).values_list(
            "student_id", flat=True
        )
    ) == before


def test_gym_afr_009(stub_iam, gym_context):
    """test_id=GYM-AFR-009; source_id=AFR-GYM-009 Current leadership assignments"""
    head = _client(stub_iam, 101, ("gymkhana.leadership.update",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/leadership/",
        {"new_coordinator_id": 103, "new_co_coordinator_id": 104},
        format="json",
    )
    assert response.status_code == 200
    current = set(
        ClubLeadership.objects.filter(club=gym_context.club, is_current=True).values_list(
            "role", "student_id"
        )
    )
    assert current == {("coordinator", 103), ("co_coordinator", 104)}
    assert not ClubLeadership.objects.filter(
        club=gym_context.club, student_id__in=(101, 102), is_current=True
    ).exists()


def test_gym_afr_010(stub_iam, gym_context):
    """test_id=GYM-AFR-010; source_id=AFR-GYM-010 Session booking"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    response = _book(head, gym_context.club.id, "session", _booking_payload())
    assert response.status_code == 201
    assert ClubBooking.objects.filter(
        pk=response.json()["id"],
        booking_type="session",
        venue="L-101",
        date=BOOKING_DATE,
        start_time=time(10),
        end_time=time(12),
    ).exists()


def test_gym_afr_011_valid(stub_iam, gym_context):
    """test_id=GYM-AFR-011-valid; source_id=AFR-GYM-011 Valid time range"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    response = _book(
        head, gym_context.club.id, "session",
        _booking_payload(start_time="10:00:00", end_time="10:01:00"),
    )
    assert response.status_code == 201
    assert ClubBooking.objects.filter(pk=response.json()["id"]).exists()


def test_gym_afr_011_equal(stub_iam, gym_context):
    """test_id=GYM-AFR-011-equal; source_id=AFR-GYM-011 Equal time boundary"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    initial_count = ClubBooking.objects.count()
    response = _book(
        head, gym_context.club.id, "session",
        _booking_payload(start_time="10:00:00", end_time="10:00:00"),
    )
    assert response.status_code == 422
    assert ClubBooking.objects.count() == initial_count


def test_gym_afr_011_reversed(stub_iam, gym_context):
    """test_id=GYM-AFR-011-reversed; source_id=AFR-GYM-011 Reversed time range"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    initial_count = ClubBooking.objects.count()
    response = _book(
        head, gym_context.club.id, "session",
        _booking_payload(start_time="12:00:00", end_time="10:00:00"),
    )
    assert response.status_code == 422
    assert ClubBooking.objects.count() == initial_count


def test_gym_afr_012_session_session(stub_iam, gym_context):
    """test_id=GYM-AFR-012-session-session; source_id=AFR-GYM-012 Session-session overlap"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    assert _book(head, gym_context.club.id, "session", _booking_payload()).status_code == 201
    initial_count = ClubBooking.objects.count()
    response = _book(
        head, gym_context.club.id, "session",
        _booking_payload(start_time="11:00:00", end_time="13:00:00"),
    )
    assert response.status_code == 409
    assert ClubBooking.objects.count() == initial_count


def test_gym_afr_012_event_event(stub_iam, gym_context):
    """test_id=GYM-AFR-012-event-event; source_id=AFR-GYM-012 Event-event overlap"""
    head = _client(stub_iam, 101, ("gymkhana.event.book",))
    assert _book(head, gym_context.club.id, "event", _booking_payload()).status_code == 201
    initial_count = ClubBooking.objects.count()
    response = _book(
        head, gym_context.club.id, "event",
        _booking_payload(start_time="11:00:00", end_time="13:00:00"),
    )
    assert response.status_code == 409
    assert ClubBooking.objects.count() == initial_count


def test_gym_afr_012_cross_type(stub_iam, gym_context):
    """test_id=GYM-AFR-012-cross-type; source_id=AFR-GYM-012 Cross-type overlap"""
    head = _client(stub_iam, 101, ("gymkhana.session.book", "gymkhana.event.book"))
    assert _book(head, gym_context.club.id, "event", _booking_payload()).status_code == 201
    after_first = ClubBooking.objects.count()
    response = _book(
        head, gym_context.club.id, "session",
        _booking_payload(start_time="11:00:00", end_time="13:00:00"),
    )
    assert response.status_code == 409
    assert ClubBooking.objects.count() == after_first

    next_date = (BOOKING_DATE + timedelta(days=1)).isoformat()
    assert _book(
        head, gym_context.club.id, "session",
        _booking_payload(
            venue="Auditorium", date=next_date,
            start_time="10:00:00", end_time="12:00:00",
        ),
    ).status_code == 201
    after_second = ClubBooking.objects.count()
    response = _book(
        head, gym_context.club.id, "event",
        _booking_payload(
            venue="Auditorium", date=next_date,
            start_time="11:00:00", end_time="13:00:00",
        ),
    )
    assert response.status_code == 409
    assert ClubBooking.objects.count() == after_second


def test_gym_afr_012_separation(stub_iam, gym_context):
    """test_id=GYM-AFR-012-separation; source_id=AFR-GYM-012 Venue and date separation"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    assert _book(head, gym_context.club.id, "session", _booking_payload()).status_code == 201
    different_venue = _book(
        head, gym_context.club.id, "session", _booking_payload(venue="Auditorium")
    )
    different_date = _book(
        head, gym_context.club.id, "session",
        _booking_payload(date=(BOOKING_DATE + timedelta(days=1)).isoformat()),
    )
    assert different_venue.status_code == 201
    assert different_date.status_code == 201
    assert ClubBooking.objects.count() == 3


def test_gym_afr_013(stub_iam, gym_context):
    """test_id=GYM-AFR-013; source_id=AFR-GYM-013 Successful session notification"""
    head = _client(stub_iam, 101, ("gymkhana.session.book",))
    response = _book(head, gym_context.club.id, "session", _booking_payload())
    assert response.status_code == 201
    notifications = GymkhanaNotificationOutbox.objects.filter(topic="gymkhana.session")
    assert set(notifications.values_list("recipient_user_id", flat=True)) == gym_context.students


def test_gym_afr_014(stub_iam, gym_context):
    """test_id=GYM-AFR-014; source_id=AFR-GYM-014 Event booking"""
    head = _client(stub_iam, 101, ("gymkhana.event.book",))
    response = _book(
        head, gym_context.club.id, "event",
        _booking_payload(title="Councillor Context Event"),
    )
    assert response.status_code == 201
    booking = ClubBooking.objects.get(pk=response.json()["id"])
    assert booking.booking_type == "event"
    assert booking.club.faculty_councillor_id == 201
    assert booking.venue == "L-101"
    assert booking.date == BOOKING_DATE


def test_gym_afr_015(stub_iam, gym_context):
    """test_id=GYM-AFR-015; source_id=AFR-GYM-015 Successful event notification"""
    head = _client(stub_iam, 101, ("gymkhana.event.book",))
    response = _book(head, gym_context.club.id, "event", _booking_payload())
    assert response.status_code == 201
    notifications = GymkhanaNotificationOutbox.objects.filter(topic="gymkhana.event")
    assert set(notifications.values_list("recipient_user_id", flat=True)) == gym_context.students


def test_gym_afr_016(stub_iam, gym_context):
    """test_id=GYM-AFR-016; source_id=AFR-GYM-016 Confirmed-club membership application"""
    student = _client(stub_iam, 103, ("gymkhana.membership.apply",))
    response = student.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/memberships/apply/",
        {"remarks": "Robotics experience and interest"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["student_id"] == 103
    assert response.json()["remarks"] == "Robotics experience and interest"


def test_gym_afr_016_open_club(stub_iam, gym_context):
    """test_id=GYM-AFR-016-open-club; source_id=AFR-GYM-016 Open-club membership restriction"""
    open_club = _make_club("Open Club Membership Target", status="open")
    student = _client(stub_iam, 103, ("gymkhana.membership.apply",))
    response = student.post(
        f"/api/v1/gymkhana/clubs/{open_club.id}/memberships/apply/",
        {"remarks": "Application"},
        format="json",
    )
    assert response.status_code == 409
    assert not ClubMembership.objects.filter(club=open_club, student_id=103).exists()


def test_gym_afr_017(stub_iam, gym_context):
    """test_id=GYM-AFR-017; source_id=AFR-GYM-017 Multiple-club applications"""
    other_club = _make_club("Second Confirmed Club")
    student = _client(stub_iam, 103, ("gymkhana.membership.apply",))
    first = student.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/memberships/apply/",
        {"remarks": "First club"},
        format="json",
    )
    second = student.post(
        f"/api/v1/gymkhana/clubs/{other_club.id}/memberships/apply/",
        {"remarks": "Second club"},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert set(
        ClubMembership.objects.filter(student_id=103).values_list("club_id", flat=True)
    ) == {gym_context.club.id, other_club.id}


def test_gym_afr_018(stub_iam, gym_context):
    """test_id=GYM-AFR-018; source_id=AFR-GYM-018 Duplicate same-club application"""
    student = _client(stub_iam, 103, ("gymkhana.membership.apply",))
    url = f"/api/v1/gymkhana/clubs/{gym_context.club.id}/memberships/apply/"
    assert student.post(url, {"remarks": "First"}, format="json").status_code == 201
    response = student.post(url, {"remarks": "Duplicate"}, format="json")
    assert response.status_code == 409
    assert ClubMembership.objects.filter(club=gym_context.club, student_id=103).count() == 1


def test_gym_afr_019(stub_iam, gym_context):
    """test_id=GYM-AFR-019; source_id=AFR-GYM-019 Application open status"""
    student = _client(stub_iam, 103, ("gymkhana.membership.apply",))
    response = student.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/memberships/apply/",
        {"remarks": "Interested"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert ClubMembership.objects.get(pk=response.json()["id"]).status == "open"


def test_gym_afr_020_authorized(stub_iam, gym_context):
    """test_id=GYM-AFR-020-authorized; source_id=AFR-GYM-020 Applicable Club Head access"""
    application = ClubMembership.objects.create(
        club=gym_context.club, student_id=103, status="open"
    )
    head = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = head.get(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/memberships/?status=open"
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [application.id]


def test_gym_afr_020_unauthorized(stub_iam, gym_context):
    """test_id=GYM-AFR-020-unauthorized; source_id=AFR-GYM-020 Club Head authorization"""
    application = ClubMembership.objects.create(
        club=gym_context.club, student_id=104, status="open"
    )
    non_head = _client(stub_iam, 103, ("gymkhana.membership.approve",))
    response = non_head.get(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/memberships/?status=open"
    )
    assert response.status_code == 404
    application.refresh_from_db()
    assert application.status == "open"


def test_gym_afr_021(stub_iam, gym_context):
    """test_id=GYM-AFR-021; source_id=AFR-GYM-021 Approval with optional remarks"""
    first = ClubMembership.objects.create(
        club=gym_context.club, student_id=103, status="open"
    )
    second = ClubMembership.objects.create(
        club=gym_context.club, student_id=104, status="open"
    )
    head = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    no_remarks = head.post(
        f"/api/v1/gymkhana/memberships/{first.id}/approve/", {}, format="json"
    )
    with_remarks = head.post(
        f"/api/v1/gymkhana/memberships/{second.id}/approve/",
        {"remarks": "Welcome to the club"},
        format="json",
    )
    assert no_remarks.status_code == 200
    assert with_remarks.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == "confirmed"
    assert first.remarks == ""
    assert second.status == "confirmed"
    assert second.remarks == "Welcome to the club"


def test_gym_afr_021_unauthorized(stub_iam, gym_context):
    """test_id=GYM-AFR-021-unauthorized; source_id=AFR-GYM-021 Applicable Club Head authorization"""
    application = ClubMembership.objects.create(
        club=gym_context.club, student_id=104, status="open"
    )
    non_head = _client(stub_iam, 103, ("gymkhana.membership.approve",))
    response = non_head.post(
        f"/api/v1/gymkhana/memberships/{application.id}/approve/",
        {"remarks": "Not authorized"},
        format="json",
    )
    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == "open"


def test_gym_afr_022(stub_iam, gym_context):
    """test_id=GYM-AFR-022; source_id=AFR-GYM-022 Approved application confirmed"""
    application = ClubMembership.objects.create(
        club=gym_context.club, student_id=103, status="open"
    )
    head = _client(stub_iam, 101, ("gymkhana.membership.approve",))
    response = head.post(
        f"/api/v1/gymkhana/memberships/{application.id}/approve/", {}, format="json"
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == "confirmed"


def test_gym_afr_023(stub_iam, gym_context):
    """test_id=GYM-AFR-023; source_id=AFR-GYM-023 Voting poll creation"""
    head = _client(stub_iam, 101, ("gymkhana.poll.create",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["target_batches"] == ["2023"]
    assert payload["target_branches"] == ["CSE"]
    assert [choice["text"] for choice in payload["choices"]] == ["Option A", "Option B"]
    assert datetime.fromisoformat(payload["expires_at"]) > timezone.now()
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    assert any(
        poll["id"] == payload["id"]
        for poll in student.get("/api/v1/gymkhana/polls/").json()
    )


def test_gym_afr_024_valid(stub_iam, gym_context):
    """test_id=GYM-AFR-024-valid; source_id=AFR-GYM-024 Two-choice boundary"""
    head = _client(stub_iam, 101, ("gymkhana.poll.create",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
        _poll_payload(choices=["Only A", "Only B"]),
        format="json",
    )
    assert response.status_code == 201
    assert len(response.json()["choices"]) == 2


def test_gym_afr_024_invalid(stub_iam, gym_context):
    """test_id=GYM-AFR-024-invalid; source_id=AFR-GYM-024 Fewer than two choices"""
    head = _client(stub_iam, 101, ("gymkhana.poll.create",))
    initial_count = VotingPoll.objects.count()
    for choices in ([], ["Only one"]):
        response = head.post(
            f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
            _poll_payload(choices=choices),
            format="json",
        )
        assert response.status_code == 422
        assert VotingPoll.objects.count() == initial_count


def test_gym_afr_025(stub_iam, gym_context):
    """test_id=GYM-AFR-025; source_id=AFR-GYM-025 Poll target notifications"""
    head = _client(stub_iam, 101, ("gymkhana.poll.create",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert response.status_code == 201
    notifications = GymkhanaNotificationOutbox.objects.filter(
        topic="gymkhana.poll.created"
    )
    assert set(notifications.values_list("recipient_user_id", flat=True)) == {101, 102, 103}


def test_gym_afr_026_targeted_active(stub_iam, gym_context):
    """test_id=GYM-AFR-026-targeted-active; source_id=AFR-GYM-026 Eligible active poll access"""
    poll = VotingPoll.objects.create(
        club=gym_context.club,
        title="Active Poll",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() + timedelta(days=1),
        created_by_id=101,
    )
    choices = [
        PollChoice.objects.create(poll=poll, text="Choice A"),
        PollChoice.objects.create(poll=poll, text="Choice B"),
    ]
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = student.get("/api/v1/gymkhana/polls/")
    assert response.status_code == 200
    result = next(row for row in response.json() if row["id"] == poll.id)
    assert {row["id"] for row in result["choices"]} == {choice.id for choice in choices}


def test_gym_afr_026_untargeted(stub_iam, gym_context):
    """test_id=GYM-AFR-026-untargeted; source_id=AFR-GYM-026 Untargeted student access"""
    poll = VotingPoll.objects.create(
        club=gym_context.club,
        title="CSE Poll",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() + timedelta(days=1),
        created_by_id=101,
    )
    PollChoice.objects.create(poll=poll, text="Choice A")
    PollChoice.objects.create(poll=poll, text="Choice B")
    untargeted = _client(stub_iam, 105, ("gymkhana.poll.vote",))
    response = untargeted.get("/api/v1/gymkhana/polls/")
    assert response.status_code == 200
    assert poll.id not in {row["id"] for row in response.json()}


def test_gym_afr_026_expired(stub_iam, gym_context):
    """test_id=GYM-AFR-026-expired; source_id=AFR-GYM-026 Expired poll access"""
    poll = VotingPoll.objects.create(
        club=gym_context.club,
        title="Expired Poll",
        target_batches=["2023"],
        target_branches=["CSE"],
        expires_at=timezone.now() - timedelta(seconds=1),
        created_by_id=101,
    )
    choice = PollChoice.objects.create(poll=poll, text="Choice A")
    PollChoice.objects.create(poll=poll, text="Choice B")
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    listed = student.get("/api/v1/gymkhana/polls/")
    assert listed.status_code == 200
    assert poll.id not in {row["id"] for row in listed.json()}
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert response.status_code == 409
    assert not PollVote.objects.filter(poll=poll).exists()


def test_gym_afr_027(stub_iam, gym_context):
    """test_id=GYM-AFR-027; source_id=AFR-GYM-027 Eligible student vote"""
    poll_response = _client(stub_iam, 101, ("gymkhana.poll.create",)).post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert poll_response.status_code == 201
    poll_id = poll_response.json()["id"]
    choice_id = poll_response.json()["choices"][0]["id"]
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )
    assert response.status_code == 200
    assert PollVote.objects.filter(
        poll_id=poll_id, student_id=103, choice_id=choice_id
    ).exists()


def test_gym_afr_028_duplicate(stub_iam, gym_context):
    """test_id=GYM-AFR-028-duplicate; source_id=AFR-GYM-028 Duplicate vote prevention"""
    poll_response = _client(stub_iam, 101, ("gymkhana.poll.create",)).post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert poll_response.status_code == 201
    poll_id = poll_response.json()["id"]
    choices = poll_response.json()["choices"]
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    first = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choices[0]["id"]},
        format="json",
    )
    assert first.status_code == 200
    response = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choices[1]["id"]},
        format="json",
    )
    assert response.status_code == 409
    assert PollVote.objects.filter(poll_id=poll_id, student_id=103).count() == 1


def test_gym_afr_028_tally(stub_iam, gym_context):
    """test_id=GYM-AFR-028-tally; source_id=AFR-GYM-028 Accepted vote tally"""
    poll_response = _client(stub_iam, 101, ("gymkhana.poll.create",)).post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/polls/",
        _poll_payload(),
        format="json",
    )
    assert poll_response.status_code == 201
    poll_id = poll_response.json()["id"]
    choice_id = poll_response.json()["choices"][0]["id"]
    before = PollChoice.objects.get(pk=choice_id).votes_count
    student = _client(stub_iam, 103, ("gymkhana.poll.vote",))
    vote = student.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )
    assert vote.status_code == 200
    listed = student.get("/api/v1/gymkhana/polls/")
    assert listed.status_code == 200
    poll = next(row for row in listed.json() if row["id"] == poll_id)
    selected_choice = next(row for row in poll["choices"] if row["id"] == choice_id)
    assert selected_choice["votes_count"] == before + 1


def test_gym_afr_029(stub_iam, gym_context):
    """test_id=GYM-AFR-029; source_id=AFR-GYM-029 Budget request submission"""
    head = _client(stub_iam, 101, ("gymkhana.budget.request",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/budgets/",
        {
            "amount": "1250.50",
            "purpose": "Equipment",
            "description": "Replacement equipment",
            "supporting_file": SimpleUploadedFile(
                "budget.pdf", b"%PDF-1.4 budget", content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert response.status_code == 201
    request = ClubBudgetRequest.objects.get(pk=response.json()["id"])
    assert request.amount == Decimal("1250.50")
    assert request.purpose == "Equipment"
    assert request.supporting_file


def test_gym_afr_030_negative(stub_iam, gym_context):
    """test_id=GYM-AFR-030-negative; source_id=AFR-GYM-030 Negative budget amount"""
    head = _client(stub_iam, 101, ("gymkhana.budget.request",))
    initial_count = ClubBudgetRequest.objects.count()
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/budgets/",
        {
            "amount": "-1.00",
            "purpose": "Equipment",
            "description": "Invalid amount",
            "supporting_file": SimpleUploadedFile(
                "budget.pdf", b"%PDF-1.4 budget", content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert response.status_code == 422
    assert ClubBudgetRequest.objects.count() == initial_count


def test_gym_afr_030_missing_file(stub_iam, gym_context):
    """test_id=GYM-AFR-030-missing-file; source_id=AFR-GYM-030 Missing supporting file"""
    head = _client(stub_iam, 101, ("gymkhana.budget.request",))
    initial_count = ClubBudgetRequest.objects.count()
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/budgets/",
        {"amount": "100.00", "purpose": "Equipment", "description": "File omitted"},
        format="multipart",
    )
    assert response.status_code == 422
    assert ClubBudgetRequest.objects.count() == initial_count


def test_gym_afr_031(stub_iam, gym_context):
    """test_id=GYM-AFR-031; source_id=AFR-GYM-031 Open budget request tracking"""
    head = _client(stub_iam, 101, ("gymkhana.budget.request",))
    response = head.post(
        f"/api/v1/gymkhana/clubs/{gym_context.club.id}/budgets/",
        {
            "amount": "100.00",
            "purpose": "Supplies",
            "description": "Tracking-only request",
            "supporting_file": SimpleUploadedFile(
                "budget.pdf", b"%PDF-1.4 budget", content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert response.status_code == 201
    request_id = response.json()["id"]
    request = ClubBudgetRequest.objects.get(pk=request_id)
    assert request.status == "open"
    listed = head.get(f"/api/v1/gymkhana/clubs/{gym_context.club.id}/budgets/")
    assert listed.status_code == 200
    assert next(row for row in listed.json() if row["id"] == request_id)["status"] == "open"
    action_routes = [
        route for route in _all_route_strings()
        if "budget" in route.lower() and re.search(r"/(approve|reject)/?$", route.lower())
    ]
    assert action_routes == []


def test_gym_afr_032(stub_iam, gym_context):
    """test_id=GYM-AFR-032; source_id=AFR-GYM-032 Event report submission"""
    head = _client(stub_iam, 101, ("gymkhana.report.submit",))
    response = _create_report(head, gym_context.club.id)
    assert response.status_code == 201
    report = ClubEventReport.objects.get(pk=response.json()["id"])
    assert report.club_id == gym_context.club.id
    assert report.student_incharge_id == 103
    assert report.event_name == "Annual Event"
    assert report.report_file


def test_gym_afr_033(stub_iam, gym_context):
    """test_id=GYM-AFR-033; source_id=AFR-GYM-033 Required report file"""
    head = _client(stub_iam, 101, ("gymkhana.report.submit",))
    initial_count = ClubEventReport.objects.count()
    response = _create_report(head, gym_context.club.id, file=False)
    assert response.status_code == 422
    assert ClubEventReport.objects.count() == initial_count


def test_gym_afr_034_assigned(stub_iam, gym_context):
    """test_id=GYM-AFR-034-assigned; source_id=AFR-GYM-034 Assigned councillor access"""
    report_response = _create_report(
        _client(stub_iam, 101, ("gymkhana.report.submit",)), gym_context.club.id
    )
    assert report_response.status_code == 201
    councillor = _client(stub_iam, 201, ("gymkhana.report.review",), kind="faculty")
    response = councillor.get(f"/api/v1/gymkhana/clubs/{gym_context.club.id}/reports/")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [report_response.json()["id"]]


def test_gym_afr_034_unassigned(stub_iam, gym_context):
    """test_id=GYM-AFR-034-unassigned; source_id=AFR-GYM-034 Unassigned councillor prohibition"""
    report_response = _create_report(
        _client(stub_iam, 101, ("gymkhana.report.submit",)), gym_context.club.id
    )
    assert report_response.status_code == 201
    councillor = _client(stub_iam, 202, ("gymkhana.report.review",), kind="faculty")
    response = councillor.get(f"/api/v1/gymkhana/clubs/{gym_context.club.id}/reports/")
    assert response.status_code == 404
    assert ClubEventReport.objects.filter(pk=report_response.json()["id"]).exists()
    file_response = councillor.get(
        f"/api/v1/gymkhana/reports/{report_response.json()['id']}/file/"
    )
    assert file_response.status_code == 404
