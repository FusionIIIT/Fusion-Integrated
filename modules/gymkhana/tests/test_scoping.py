"""Tests for object-level scoping selectors (BR-GYM-010, BR-GYM-021)."""
from __future__ import annotations

import datetime

import pytest
from django.http import Http404
from django.utils import timezone

from conftest import make_principal
from fusion_auth.client import UserRef as IamUserRef
from modules.gymkhana.models import (
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubMembership,
    Poll,
    PollTarget,
)
from modules.gymkhana.selectors.scoping import (
    get_managed_club,
    visible_budget_requests,
    visible_clubs,
    visible_event_reports,
    visible_memberships,
    visible_polls,
)


@pytest.fixture
def clubs():
    c1 = Club.objects.create(
        name="Robotics Club",
        category="Technical",
        description="Build bots",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        status="confirmed",
    )
    c2 = Club.objects.create(
        name="Astronomy Club",
        category="Technical",
        description="Stargazing",
        coordinator_id=103,
        co_coordinator_id=104,
        faculty_councillor_id=502,
        status="open",
    )
    return c1, c2


@pytest.mark.django_db
def test_get_managed_club_scoping(clubs):
    c1, _ = clubs
    # Coordinator succeeds
    assert get_managed_club(c1.id, 101) == c1
    # Co-coordinator succeeds
    assert get_managed_club(c1.id, 102) == c1

    # Unauthorized student raises Http404 (BR-GYM-010)
    with pytest.raises(Http404):
        get_managed_club(c1.id, 999)

    # Nonexistent club raises Http404
    with pytest.raises(Http404):
        get_managed_club(9999, 101)


@pytest.mark.django_db
def test_visible_clubs_scoping(clubs):
    c1, c2 = clubs
    # Student admin with club approve permission sees all
    admin_principal = make_principal(
        user_id=1,
        permissions=("gymkhana.club.approve",),
        roles=("Dean_s",),
    )
    assert set(visible_clubs(admin_principal)) == {c1, c2}

    # Regular student sees only confirmed clubs
    student_principal = make_principal(user_id=201, roles=("student",))
    assert list(visible_clubs(student_principal)) == [c1]


@pytest.mark.django_db
def test_visible_memberships_scoping(clubs):
    c1, c2 = clubs
    m1 = ClubMembership.objects.create(club=c1, student_id=201, status="confirmed")
    m2 = ClubMembership.objects.create(club=c2, student_id=201, status="open")
    m3 = ClubMembership.objects.create(club=c1, student_id=202, status="open")

    student_principal = make_principal(user_id=201, roles=("student",))
    # Student viewing their own memberships
    student_memberships = list(visible_memberships(student_principal))
    assert set(student_memberships) == {m1, m2}

    # Club coordinator viewing applications for managed club
    coord_principal = make_principal(user_id=101, roles=("co-ordinator",))
    club1_memberships = list(visible_memberships(coord_principal, club_id=c1.id))
    assert set(club1_memberships) == {m1, m3}

    # Coordinator of club 1 trying to view club 2 memberships raises Http404
    with pytest.raises(Http404):
        visible_memberships(coord_principal, club_id=c2.id)


@pytest.mark.django_db
def test_visible_polls_scoping(clubs, stub_iam):
    c1, _ = clubs
    now = timezone.now()
    future = now + datetime.timedelta(days=2)
    past = now - datetime.timedelta(days=1)

    # Poll 1: Active, targeting 2024 CSE
    p1 = Poll.objects.create(
        club=c1, title="CSE Poll", description="For CSE", expires_at=future,
        status="active", created_by_user_id=101,
    )
    PollTarget.objects.create(poll=p1, batch_year=2024, discipline="CSE")

    # Poll 2: Active, targeting 2024 all disciplines
    p2 = Poll.objects.create(
        club=c1, title="All Disciplines Poll", description="For 2024", expires_at=future,
        status="active", created_by_user_id=101,
    )
    PollTarget.objects.create(poll=p2, batch_year=2024, discipline="all")

    # Poll 3: Active, targeting 2023 ECE
    p3 = Poll.objects.create(
        club=c1, title="ECE Poll", description="For ECE", expires_at=future,
        status="active", created_by_user_id=101,
    )
    PollTarget.objects.create(poll=p3, batch_year=2023, discipline="ECE")

    # Poll 4: Expired, targeting 2024 CSE
    p4 = Poll.objects.create(
        club=c1, title="Expired Poll", description="Expired", expires_at=past,
        status="active", created_by_user_id=101,
    )
    PollTarget.objects.create(poll=p4, batch_year=2024, discipline="CSE")

    # Stub student 201: batch 2024, CSE via IamUserRef
    student_ref = IamUserRef(
        user_id=201,
        username="u201",
        display_name="Student CSE",
        kind="student",
        discipline="CSE",
        batch_year=2024,
    )
    stub_iam(users={201: student_ref})

    student_principal = make_principal(user_id=201, roles=("student",))

    visible = list(visible_polls(student_principal))
    assert set(visible) == {p1, p2}
    assert p3 not in visible
    assert p4 not in visible


@pytest.mark.django_db
def test_visible_event_reports_faculty_scoping(clubs):
    c1, c2 = clubs
    # c1 has faculty_councillor_id=501
    # c2 has faculty_councillor_id=502

    r1 = ClubEventReport.objects.create(
        club=c1,
        event_name="RoboExpo 2026",
        event_date=datetime.date(2026, 11, 20),
        event_time=datetime.time(14, 0),
        description="Annual expo",
        student_incharge_id=201,
        report_file_url="https://drive.google.com/file/d/1234567890/view",
        report_file_id="1234567890",
        submitted_by_user_id=101,
    )
    r2 = ClubEventReport.objects.create(
        club=c2,
        event_name="StarWatch 2026",
        event_date=datetime.date(2026, 11, 21),
        event_time=datetime.time(20, 0),
        description="Night sky watch",
        student_incharge_id=202,
        report_file_url="https://drive.google.com/file/d/0987654321/view",
        report_file_id="0987654321",
        submitted_by_user_id=103,
    )

    # Faculty 501: can see r1, cannot see r2 (BR-GYM-021)
    faculty_501 = make_principal(user_id=501, roles=("faculty",))
    faculty_reports = list(visible_event_reports(faculty_501))
    assert faculty_reports == [r1]

    # Specific report lookup: r1 succeeds, r2 raises Http404
    assert list(visible_event_reports(faculty_501, report_id=r1.id)) == [r1]
    with pytest.raises(Http404):
        visible_event_reports(faculty_501, report_id=r2.id)

    # Coordinator 101: can view r1 for their club, but not r2
    coord_101 = make_principal(user_id=101, roles=("co-ordinator",))
    assert list(visible_event_reports(coord_101, club_id=c1.id)) == [r1]
    with pytest.raises(Http404):
        visible_event_reports(coord_101, club_id=c2.id)


@pytest.mark.django_db
def test_visible_budget_requests_scoping(clubs):
    c1, _ = clubs
    req1 = ClubBudgetRequest.objects.create(
        club=c1,
        amount=5000,
        purpose="Parts purchase",
        description="Motors and sensors",
        supporting_file_url="https://drive.google.com/file/d/1111111111/view",
        supporting_file_id="1111111111",
        status="open",
        submitted_by_user_id=101,
    )

    coord_101 = make_principal(user_id=101, roles=("co-ordinator",))
    assert list(visible_budget_requests(coord_101, club_id=c1.id)) == [req1]

    # Coordinator 103 (club 2) cannot access club 1 budget requests
    coord_103 = make_principal(user_id=103, roles=("co-ordinator",))
    with pytest.raises(Http404):
        visible_budget_requests(coord_103, club_id=c1.id)
