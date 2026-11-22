"""
Tests for Gymkhana privilege escalation defenses and role authorization.
"""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana.models import Club, ClubEventReport, ClubLeadership, ClubMembership

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=101, permissions=(), modules=("gymkhana",)):
    stub_iam(make_session(user_id=user_id, modules=modules, permissions=permissions))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_regular_student_cannot_confirm_club(stub_iam):
    club = Club.objects.create(name="Open Club", category="Technical", status="open")
    client = _auth_client(
        stub_iam,
        user_id=201,
        permissions=("gymkhana.club.view", "gymkhana.membership.apply"),
    )
    # Missing gymkhana.club.admin
    resp = client.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert resp.status_code == 403


def test_non_coordinator_cannot_approve_memberships(stub_iam):
    club = Club.objects.create(name="Astronomy Club", category="Technical", status="confirmed")
    ClubLeadership.objects.create(
        club=club,
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        is_active=True,
    )
    mem = ClubMembership.objects.create(club=club, student_id=301, status="open")

    # User 999 lacks coordinator authorization
    client = _auth_client(
        stub_iam,
        user_id=999,
        permissions=("gymkhana.club.manage",),
    )
    resp = client.post(f"/api/v1/gymkhana/memberships/{mem.id}/approve/")
    assert resp.status_code in (400, 403)
    mem.refresh_from_db()
    assert mem.status == "open"


def test_unassigned_faculty_cannot_review_event_report(stub_iam):
    club = Club.objects.create(name="Robotics Club", category="Technical", status="confirmed")
    ClubLeadership.objects.create(
        club=club,
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        is_active=True,
    )
    report = ClubEventReport.objects.create(
        club=club,
        event_name="Workshop",
        event_date="2026-11-15",
        report_file="report.pdf",
        submitted_by_id=101,
    )

    # Faculty 502 is not the assigned councillor (501)
    faculty_client = _auth_client(
        stub_iam,
        user_id=502,
        permissions=("gymkhana.report.review",),
    )
    resp = faculty_client.get(f"/api/v1/gymkhana/reports/{report.id}/review/")
    assert resp.status_code == 403
