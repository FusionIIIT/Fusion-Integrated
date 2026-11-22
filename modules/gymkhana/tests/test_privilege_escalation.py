"""Write authority is a permission, not read scope.

A student can SEE a club or active polls, which is exactly why the write paths
must check permissions and roles.
"""
import pytest
from django.apps import apps
from django.test import override_settings
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana import registry
from modules.gymkhana.models import Club

pytestmark = pytest.mark.django_db

ROOT = "/api/v1/gymkhana"
STUDENT_ROLE_PERMS = tuple(registry.ROLE_GRANTS["student"])
STUDENT_ADMIN_PERMS = tuple(registry.ROLE_GRANTS["Student Admin"])
FACULTY_PERMS = tuple(registry.ROLE_GRANTS["faculty"])


def _client(stub_iam, *, user_id=2001, kind="student", role="student", permissions=None,
            modules=("gymkhana",)):
    grants = permissions if permissions is not None else registry.ROLE_GRANTS.get(role, ())
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=(role,),
        active_role=role,
        modules=modules,
        permissions=grants,
    ))
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


def _club(*, coordinator_id=2001, status=Club.Status.CONFIRMED):
    return Club.objects.create(
        name="Music Club",
        category="Cultural",
        coordinator_user_id=coordinator_id,
        co_coordinator_user_id=coordinator_id + 1,
        faculty_councillor_user_id=3001,
        description="Music enthusiasts",
        status=status,
    )


def test_plain_student_cannot_create_or_confirm_club(stub_iam):
    _person(2001, "student")
    _person(2002, "student")
    _person(3001, "faculty")
    student = _client(stub_iam, user_id=2001, role="student", permissions=STUDENT_ROLE_PERMS)

    # Creating a club requires gymkhana.club.manage (Student Admin)
    post_res = student.post(f"{ROOT}/clubs", {
        "name": "Robotics Club",
        "category": "Technical",
        "coordinator_user_id": 2001,
        "co_coordinator_user_id": 2002,
        "faculty_councillor_user_id": 3001,
        "description": "Tech",
    }, format="json")
    assert post_res.status_code == 403

    # Confirming a club requires gymkhana.club.manage
    club = _club(coordinator_id=2001, status=Club.Status.OPEN)
    confirm_res = student.post(f"{ROOT}/clubs/{club.pk}/approve")
    assert confirm_res.status_code == 403


@override_settings(GYMKHANA_VENUES=("Auditorium",))
def test_plain_student_cannot_act_as_club_head(stub_iam):
    _person(2001, "student")
    _person(2002, "student")
    _person(2005, "student")  # not in club leadership
    _person(3001, "faculty")
    club = _club(coordinator_id=2001)

    outsider = _client(stub_iam, user_id=2005, role="student", permissions=STUDENT_ROLE_PERMS)

    # Cannot book session
    res = outsider.post(f"{ROOT}/clubs/{club.pk}/sessions", {
        "venue": "Auditorium",
        "date": "2026-12-01",
        "start_time": "17:00:00",
        "end_time": "18:00:00",
    }, format="json")
    assert res.status_code == 403

    # Cannot book event
    res = outsider.post(f"{ROOT}/clubs/{club.pk}/events", {
        "name": "Gig",
        "venue": "Auditorium",
        "date": "2026-12-02",
        "start_time": "17:00:00",
        "end_time": "18:00:00",
    }, format="json")
    assert res.status_code == 403

    # Cannot change leadership
    res = outsider.post(f"{ROOT}/clubs/{club.pk}/leadership", {
        "coordinator_user_id": 2005,
        "co_coordinator_user_id": 2002,
    }, format="json")
    assert res.status_code == 403

    # Cannot create poll for club
    res = outsider.post(f"{ROOT}/polls", {
        "club_id": club.pk,
        "title": "T-shirt design",
        "description": "Vote on design",
        "expires_at": "2026-12-31T23:59:59+05:30",
        "choices": ["Design A", "Design B"],
        "target_groups": [{"batch_year": 2024, "discipline": "CSE"}],
    }, format="json")
    assert res.status_code == 403


def test_student_cannot_view_assigned_reports_endpoint(stub_iam):
    _person(2001, "student")
    student = _client(stub_iam, user_id=2001, role="student", permissions=STUDENT_ROLE_PERMS)
    res = student.get(f"{ROOT}/reports/assigned")
    assert res.status_code == 403


def test_unauthenticated_request_is_refused():
    c = APIClient()
    res = c.get(f"{ROOT}/clubs")
    assert res.status_code in (401, 403)
