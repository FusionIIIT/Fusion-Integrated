"""Scoping isolation: A leader in one club cannot act on or read private data of another.

Every read and write must be scoped to the caller's club authority.
"""
import pytest
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana import registry
from modules.gymkhana.models import Club, MembershipApplication

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
STUDENT_PERMS = tuple(registry.ROLE_GRANTS["student"])
FACULTY_PERMS = tuple(registry.ROLE_GRANTS["faculty"])


def _set_user(stub_iam, *, user_id, kind="student", role=None, permissions=None):
    role = role or kind
    grants = permissions if permissions is not None else registry.ROLE_GRANTS.get(role, ())
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=(role,),
        active_role=role,
        modules=("gymkhana",),
        permissions=grants,
    ))


def _client(stub_iam, *, user_id=2001, kind="student", role="student", permissions=None,
            modules=("gymkhana",)):
    _set_user(stub_iam, user_id=user_id, kind=kind, role=role, permissions=permissions)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def _person(user_id, kind, *, batch_year=2024, discipline="CSE"):
    user_ref_cls = apps.get_model("directory", "UserRef")
    return user_ref_cls.objects.create(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"Person {user_id}",
        kind=kind,
        batch_year=batch_year if kind == "student" else None,
        discipline=discipline if kind == "student" else "",
    )


def _setup_two_clubs():
    _person(2001, "student")  # Head of Club A
    _person(2002, "student")  # Co-Head of Club A
    _person(2003, "student")  # Head of Club B
    _person(2004, "student")  # Co-Head of Club B
    _person(3001, "faculty")  # Councillor Club A
    _person(3002, "faculty")  # Councillor Club B

    club_a = Club.objects.create(
        name="Club Alpha",
        category="Technical",
        coordinator_user_id=2001,
        co_coordinator_user_id=2002,
        faculty_councillor_user_id=3001,
        description="Alpha club",
        status=Club.Status.CONFIRMED,
    )
    club_b = Club.objects.create(
        name="Club Beta",
        category="Cultural",
        coordinator_user_id=2003,
        co_coordinator_user_id=2004,
        faculty_councillor_user_id=3002,
        description="Beta club",
        status=Club.Status.CONFIRMED,
    )
    return club_a, club_b


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_club_a_head_cannot_book_or_manage_club_b(stub_iam):
    _club_a, club_b = _setup_two_clubs()
    head_a = _client(stub_iam, user_id=2001, permissions=STUDENT_PERMS)

    # Cannot book session for Club B
    res = head_a.post(f"{ROOT}/clubs/{club_b.pk}/sessions", {
        "venue": "Auditorium",
        "date": "2026-12-10",
        "start_time": "10:00:00",
        "end_time": "12:00:00",
    }, format="json")
    assert res.status_code == 403

    # Cannot book event for Club B
    res = head_a.post(f"{ROOT}/clubs/{club_b.pk}/events", {
        "name": "Beta Show",
        "venue": "Auditorium",
        "date": "2026-12-10",
        "start_time": "14:00:00",
        "end_time": "16:00:00",
    }, format="json")
    assert res.status_code == 403

    # Cannot submit budget for Club B
    res = head_a.post(
        f"{ROOT}/clubs/{club_b.pk}/budgets",
        {
            "amount": "5000",
            "purpose": "Hacking",
            "description": "Beta materials",
            "supporting_file": SimpleUploadedFile("quote.txt", b"vendor quote"),
        },
        format="multipart",
    )
    assert res.status_code == 403

    # Cannot submit report for Club B
    res = head_a.post(
        f"{ROOT}/clubs/{club_b.pk}/reports",
        {
            "student_incharge_user_id": 2001,
            "event_name": "Infiltration",
            "event_at": "2026-11-01T12:00:00+05:30",
            "description": "Cross-club report",
            "report_file": SimpleUploadedFile("report.txt", b"fake report"),
        },
        format="multipart",
    )
    assert res.status_code == 403

    # Cannot change leadership of Club B
    res = head_a.post(f"{ROOT}/clubs/{club_b.pk}/leadership", {
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
    }, format="json")
    assert res.status_code == 403


def test_club_a_head_cannot_review_club_b_applications(stub_iam):
    _club_a, club_b = _setup_two_clubs()
    applicant_id = 2010
    _person(applicant_id, "student")

    # Create application for Club B
    app = MembershipApplication.objects.create(
        club=club_b,
        student_user_id=applicant_id,
        description="I love Beta",
        status=MembershipApplication.Status.OPEN,
    )

    head_a = _client(stub_iam, user_id=2001, permissions=STUDENT_PERMS)

    # Head A cannot see Club B's application list
    res = head_a.get(f"{ROOT}/clubs/{club_b.pk}/memberships")
    assert res.status_code == 403

    # Head A cannot approve Club B's application
    res = head_a.post(f"{ROOT}/clubs/{club_b.pk}/memberships/{app.pk}/approve")
    assert res.status_code == 403


def test_faculty_councillor_only_sees_assigned_reports(stub_iam):
    club_a, club_b = _setup_two_clubs()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")

    # Head A submits report for Club A
    _set_user(stub_iam, user_id=2001, permissions=STUDENT_PERMS)
    res_a = client.post(
        f"{ROOT}/clubs/{club_a.pk}/reports",
        {
            "student_incharge_user_id": 2001,
            "event_name": "Alpha Showcase",
            "event_at": "2026-11-01T12:00:00+05:30",
            "description": "Alpha report",
            "report_file": SimpleUploadedFile("alpha.txt", b"alpha details"),
        },
        format="multipart",
    )
    assert res_a.status_code == 201

    # Head B submits report for Club B
    _set_user(stub_iam, user_id=2003, permissions=STUDENT_PERMS)
    res_b = client.post(
        f"{ROOT}/clubs/{club_b.pk}/reports",
        {
            "student_incharge_user_id": 2003,
            "event_name": "Beta Festival",
            "event_at": "2026-11-02T12:00:00+05:30",
            "description": "Beta report",
            "report_file": SimpleUploadedFile("beta.txt", b"beta details"),
        },
        format="multipart",
    )
    assert res_b.status_code == 201

    # Faculty Councillor of Club A logs in
    _set_user(stub_iam, user_id=3001, kind="faculty", role="faculty", permissions=FACULTY_PERMS)
    assigned = client.get(f"{ROOT}/reports/assigned").json()
    assert len(assigned["results"]) == 1
    assert assigned["results"][0]["event_name"] == "Alpha Showcase"

    # Faculty Councillor of Club A cannot download Club B's report
    report_b_id = res_b.json()["id"]
    res_dl = client.get(f"{ROOT}/files/report/{report_b_id}")
    assert res_dl.status_code in (403, 404)
