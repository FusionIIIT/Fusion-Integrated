"""Clubs (BW-GYM-03) and membership (BW-GYM-01)."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana import domain
from modules.gymkhana.models import Club, Membership

ADMIN, COORD, CO, FACULTY, STUDENT = 1, 2001, 2002, 3001, 4001
ADMIN_PERMS = ("gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve")
STUDENT_PERMS = ("gymkhana.club.view", "gymkhana.membership.create")
HEAD_PERMS = (*STUDENT_PERMS, "gymkhana.membership.approve")
NEW_CLUB = {"name": "Robotics", "category": "Technical", "coordinator_user_id": COORD,
            "co_coordinator_user_id": CO, "faculty_councillor_user_id": FACULTY}


def test_domain_rules():
    with pytest.raises(domain.RuleViolation):
        domain.check_category("Music")
    kinds = {1: "student", 2: "student", 3: "faculty"}
    domain.check_leaders(1, 2, 3, kinds)
    with pytest.raises(domain.RuleViolation):
        domain.check_leaders(1, 2, 2, kinds)
    with pytest.raises(domain.RuleViolation):
        domain.check_can_apply(domain.OPEN, False)


def _client(stub_iam, user_id, perms, users=None):
    stub_iam(make_session(user_id=user_id, modules=("gymkhana",), permissions=perms),
             users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _admin(stub_iam, user_ref):
    users = {COORD: user_ref(COORD), CO: user_ref(CO), FACULTY: user_ref(FACULTY, kind="faculty")}
    return _client(stub_iam, ADMIN, ADMIN_PERMS, users)


def _club():
    return Club.objects.create(status=domain.CONFIRMED, created_by_user_id=ADMIN, **NEW_CLUB)


@pytest.mark.django_db
def test_admin_creates_then_confirms_club(stub_iam, user_ref):
    c = _admin(stub_iam, user_ref)
    r = c.post("/api/v1/gymkhana/clubs", NEW_CLUB, format="json")
    assert r.status_code == 201 and r.json()["status"] == "open"
    r = c.post(f"/api/v1/gymkhana/clubs/{r.json()['id']}/approve")
    assert r.json()["status"] == "confirmed"


@pytest.mark.django_db
def test_duplicate_club_name_is_rejected(stub_iam, user_ref):
    _club()
    r = _admin(stub_iam, user_ref).post("/api/v1/gymkhana/clubs", NEW_CLUB, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_student_cannot_create_club(stub_iam):
    c = _client(stub_iam, STUDENT, STUDENT_PERMS)
    assert c.post("/api/v1/gymkhana/clubs", NEW_CLUB, format="json").status_code == 403


@pytest.mark.django_db
def test_apply_then_head_approves(stub_iam):
    club = _club()
    student = _client(stub_iam, STUDENT, STUDENT_PERMS)
    r = student.post("/api/v1/gymkhana/memberships", {"club": club.id}, format="json")
    assert r.status_code == 201
    again = student.post("/api/v1/gymkhana/memberships", {"club": club.id}, format="json")
    assert again.status_code == 422

    head = _client(stub_iam, COORD, HEAD_PERMS)
    r = head.post(f"/api/v1/gymkhana/memberships/{r.json()['id']}/approve", format="json")
    assert r.json()["status"] == "confirmed"


@pytest.mark.django_db
def test_other_head_cannot_approve(stub_iam):
    m = Membership.objects.create(club=_club(), user_id=STUDENT)
    head = _client(stub_iam, 9999, HEAD_PERMS)
    assert head.post(f"/api/v1/gymkhana/memberships/{m.id}/approve").status_code == 422
