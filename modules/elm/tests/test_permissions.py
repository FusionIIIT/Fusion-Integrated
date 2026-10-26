"""Security and authorization tests for ELM (BR-EL-016..020, BR-EL-036).

Strictly verifies:
1. Non-director applicants are prohibited from approving/sanctioning their own leave (BR-EL-036).
2. Director self-sanction exception applies only to the Director (BR-EL-020).
3. Cross-user operations (e.g. non-owner withdrawal, non-substitute response) are rejected.
4. Administrative endpoints require leave_admin authorization.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveBalance, LeaveRequest

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id: int, roles: tuple[str, ...], permissions: tuple[str, ...] = ()):
    all_perms = set(permissions) | {"elm.request.create", "elm.request.view"}
    stub_iam(make_session(user_id=user_id, kind="faculty", modules=("elm",), roles=roles, permissions=all_perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-test-token")
    return client


# --- BR-EL-036: Non-Director Self-Approval Prohibition ---
def test_unit_head_cannot_approve_own_cl_leave(stub_iam):
    """Unit Head (HOD) cannot approve their own CL application (BR-EL-036)."""
    LeaveBalance.objects.create(user_id=501, category="cl", year=2026, credited=Decimal("8.0"), pending=Decimal("1.0"))
    req = LeaveRequest.objects.create(
        user_id=501,
        category="cl",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 2),
        leave_days=Decimal("1.0"),
        reason="HOD personal leave",
        status=sm.PENDING_UNIT_HEAD,
    )

    hod_client = _auth_client(stub_iam, user_id=501, roles=("unit_head", "hod"), permissions=("elm.request.review",))
    resp = hod_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/unit-head-review/",
        data={"decision": "approve", "remarks": "Trying to self-approve."},
        format="json",
    )
    assert resp.status_code == 403


def test_dean_cannot_sanction_own_el_leave(stub_iam):
    """Dean cannot sanction their own EL application (BR-EL-036)."""
    LeaveBalance.objects.create(user_id=701, category="el", year=2026, credited=Decimal("30.0"), pending=Decimal("3.0"))
    req = LeaveRequest.objects.create(
        user_id=701,
        category="el",
        start_date=datetime.date(2026, 11, 3),
        end_date=datetime.date(2026, 11, 5),
        leave_days=Decimal("3.0"),
        reason="Dean official leave",
        status=sm.PENDING_SANCTION,
        unit_head_recommendation="recommended",
    )

    dean_client = _auth_client(stub_iam, user_id=701, roles=("dean",), permissions=("elm.request.sanction",))
    resp = dean_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/sanction/",
        data={"decision": "approve", "remarks": "Dean attempting self-sanction."},
        format="json",
    )
    assert resp.status_code == 403


# --- BR-EL-020: Director Self-Sanction Exception ---
def test_director_self_sanction_permitted_for_director_only(stub_iam):
    """Director may self-sanction their own leave (BR-EL-020)."""
    LeaveBalance.objects.create(user_id=1, category="el", year=2026, credited=Decimal("30.0"), pending=Decimal("2.0"))
    req = LeaveRequest.objects.create(
        user_id=1,
        category="el",
        start_date=datetime.date(2026, 11, 6),
        end_date=datetime.date(2026, 11, 7),
        leave_days=Decimal("2.0"),
        reason="Ministry meeting",
        status=sm.AWAITING_DIRECTOR_SANCTION,
    )

    director_client = _auth_client(stub_iam, user_id=1, roles=("director",), permissions=("elm.request.sanction",))
    resp = director_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/sanction/",
        data={"decision": "approve", "remarks": "Approved by Director."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.APPROVED


def test_non_director_cannot_self_sanction_under_director_path(stub_iam):
    """A non-director applicant cannot invoke self-sanction (BR-EL-020)."""
    LeaveBalance.objects.create(user_id=99, category="el", year=2026, credited=Decimal("30.0"), pending=Decimal("2.0"))
    req = LeaveRequest.objects.create(
        user_id=99,
        category="el",
        start_date=datetime.date(2026, 11, 6),
        end_date=datetime.date(2026, 11, 7),
        leave_days=Decimal("2.0"),
        reason="Imposter self-sanction",
        status=sm.AWAITING_DIRECTOR_SANCTION,
    )

    # Faculty pretending to self-sanction
    client = _auth_client(stub_iam, user_id=99, roles=("faculty",), permissions=("elm.request.sanction",))
    resp = client.post(
        f"/api/v1/elm/leave-requests/{req.id}/sanction/",
        data={"decision": "approve", "remarks": "Fake sanction."},
        format="json",
    )
    assert resp.status_code == 403


# --- Cross-Actor Isolation Tests ---
def test_non_owner_cannot_withdraw_another_employee_request(stub_iam):
    LeaveBalance.objects.create(user_id=101, category="cl", year=2026, credited=Decimal("8.0"), pending=Decimal("1.0"))
    req = LeaveRequest.objects.create(
        user_id=101,
        category="cl",
        start_date=datetime.date(2026, 11, 10),
        end_date=datetime.date(2026, 11, 10),
        leave_days=Decimal("1.0"),
        reason="Personal",
        status=sm.PENDING_UNIT_HEAD,
    )

    attacker_client = _auth_client(stub_iam, user_id=102, roles=("faculty",))
    resp = attacker_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/withdraw/",
        data={"remarks": "Malicious withdrawal attempt."},
        format="json",
    )
    assert resp.status_code == 403


def test_non_substitute_cannot_respond_to_coverage_request(stub_iam):
    LeaveBalance.objects.create(user_id=101, category="cl", year=2026, credited=Decimal("8.0"))
    req = LeaveRequest.objects.create(
        user_id=101,
        category="cl",
        start_date=datetime.date(2026, 11, 11),
        end_date=datetime.date(2026, 11, 11),
        leave_days=Decimal("1.0"),
        reason="Personal",
        substitute_id=202,
        substitute_status="pending",
        status=sm.PENDING_SUBSTITUTE,
    )

    imposter_client = _auth_client(stub_iam, user_id=303, roles=("faculty",))
    resp = imposter_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/substitute-respond/",
        data={"action": "accept", "remarks": "Imposter accept."},
        format="json",
    )
    assert resp.status_code == 403


# --- Administrative Privilege Isolation ---
def test_non_admin_cannot_trigger_year_end_rollover(stub_iam):
    faculty_client = _auth_client(stub_iam, user_id=101, roles=("faculty",))
    resp = faculty_client.post(
        "/api/v1/elm/admin/rollover/",
        data={"year": 2026},
        format="json",
    )
    assert resp.status_code == 403


def test_non_admin_cannot_publish_holiday_calendar(stub_iam):
    faculty_client = _auth_client(stub_iam, user_id=101, roles=("faculty",))
    resp = faculty_client.post(
        "/api/v1/elm/holidays/publish/",
        data={"year": 2026},
        format="json",
    )
    assert resp.status_code == 403
