"""API and workflow integration tests for ELM."""
from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.elm.domain import categories as c
from modules.elm.domain import permissions as p
from modules.elm.domain import routing as r
from modules.elm.domain import state_machine as sm
from modules.elm.domain.policy import DEFAULT_PARAMS
from modules.elm.models import LeaveRequest, LedgerEntry, PolicyVersion
from modules.elm.models.config import PUBLISHED
from modules.elm.registry import DEFAULT_HIERARCHY

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def seed_elm_policy_fixture():
    PolicyVersion.objects.create(
        name="Canonical ELM policy",
        params=DEFAULT_PARAMS,
        hierarchy=DEFAULT_HIERARCHY,
        effective_from=date(2026, 1, 1),
        status=PUBLISHED,
        published_at=timezone.now(),
    )


def _client(
    stub_iam,
    user_id=1001,
    permissions=None,
    modules=("elm",),
    kind="faculty",
    active_role="faculty",
    extra_uids=(),
):
    if permissions is None:
        permissions = (
            p.P_VIEW,
            p.P_CREATE,
            p.P_UPDATE,
            p.P_WITHDRAW,
            p.P_SUBSTITUTE,
            p.P_REVIEW,
            p.P_APPROVE,
            p.P_RESUMPTION,
            p.P_BALANCE,
            p.P_ACCOUNT_VIEW,
        )
    session = make_session(
        user_id=user_id,
        kind=kind,
        active_role=active_role,
        roles=(active_role,),
        modules=modules,
        permissions=permissions,
    )
    all_uids = {user_id, 1001, 1002, 1003, 1004, *extra_uids}
    users = {
        uid: UserRef(
            user_id=uid,
            username=f"user{uid}",
            display_name=f"User {uid}",
            kind="faculty",
            department="CSE",
            discipline="CSE",
        )
        for uid in all_uids
    }
    stub_iam(session, users=users)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def _setup_employees(user_ids: list[int]):
    pass


def _seed_balance(user_id: int, category: str, amount: Decimal, year: int = 2026):
    LedgerEntry.objects.create(
        user_id=user_id,
        category=category,
        entry_type=LedgerEntry.ANNUAL_CREDIT,
        delta=amount,
        year=year,
        note="Initial credit for testing",
    )


# ============================================================================
# Balance & Available Calculation Tests
# ============================================================================

def test_account_balances_returns_available_map(stub_iam):
    _setup_employees([1001])
    _seed_balance(1001, c.CL, Decimal("8.00"))

    # Create a pending leave request taking 3 days
    LeaveRequest.objects.create(
        user_id=1001,
        category=c.CL,
        applicant_kind="faculty",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        days=Decimal("3.00"),
        purpose="Family event",
        status=sm.AWAITING_UNIT_HEAD,
    )

    client = _client(stub_iam, user_id=1001)
    resp = client.get("/api/v1/elm/balances")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert Decimal(str(data["balances"][c.CL])) == Decimal("8.00")
    assert Decimal(str(data["pending"][c.CL])) == Decimal("3.00")
    assert Decimal(str(data["available"][c.CL])) == Decimal("5.00")


def test_leave_request_rejected_when_balance_insufficient(stub_iam):
    _setup_employees([1001])
    _seed_balance(1001, c.CL, Decimal("2.00"))

    client = _client(stub_iam, user_id=1001)
    # Applying for 3 days when available balance is only 2
    payload = {
        "category": c.CL,
        "start_date": "2026-11-02",
        "end_date": "2026-11-04",
        "purpose": "Personal work",
    }
    resp = client.post("/api/v1/elm/requests", payload, format="json")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "insufficient_balance"


def test_pending_leave_deducted_from_available_balance(stub_iam):
    _setup_employees([1001])
    _seed_balance(1001, c.CL, Decimal("8.00"))

    client = _client(stub_iam, user_id=1001)
    # First application takes 5 days (leaving 3 available)
    resp1 = client.post("/api/v1/elm/requests", {
        "category": c.CL,
        "start_date": "2026-11-02",
        "end_date": "2026-11-06",
        "purpose": "Trip 1",
    }, format="json")
    assert resp1.status_code == 201

    # Second application attempts to take 4 days (4 > 3 available)
    resp2 = client.post("/api/v1/elm/requests", {
        "category": c.CL,
        "start_date": "2026-11-16",
        "end_date": "2026-11-19",
        "purpose": "Trip 2",
    }, format="json")
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "insufficient_balance"


# ============================================================================
# BR-EL-014: Substitute Eligibility Tests
# ============================================================================

def test_self_substitute_rejected(stub_iam):
    _setup_employees([1001])
    _seed_balance(1001, c.CL, Decimal("8.00"))

    client = _client(stub_iam, user_id=1001)
    payload = {
        "category": c.CL,
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "purpose": "Leave",
        "substitute_user_id": 1001,
        "responsibility": "Cover classes",
    }
    resp = client.post("/api/v1/elm/requests", payload, format="json")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "self_substitute"


def test_substitute_overlapping_leave_rejected(stub_iam):
    _setup_employees([1001, 1002])
    _seed_balance(1001, c.CL, Decimal("8.00"))

    # Substitute 1002 already has active leave Nov 2 - Nov 5
    LeaveRequest.objects.create(
        user_id=1002,
        category=c.CL,
        applicant_kind="faculty",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 5),
        days=Decimal("4.00"),
        purpose="Away",
        status=sm.APPROVED,
    )

    client = _client(stub_iam, user_id=1001)
    payload = {
        "category": c.CL,
        "start_date": "2026-11-03",
        "end_date": "2026-11-04",
        "purpose": "Conference",
        "substitute_user_id": 1002,
        "responsibility": "Cover exams",
    }
    resp = client.post("/api/v1/elm/requests", payload, format="json")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "substitute_unavailable"


# ============================================================================
# BR-EL-034: In-Place Modification Retired
# ============================================================================

def test_inplace_modification_rejected(stub_iam):
    _setup_employees([1001])
    req = LeaveRequest.objects.create(
        user_id=1001,
        category=c.CL,
        applicant_kind="faculty",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        days=Decimal("3.00"),
        purpose="Original reason",
        status=sm.AWAITING_UNIT_HEAD,
    )

    client = _client(stub_iam, user_id=1001)
    resp = client.post(f"/api/v1/elm/requests/{req.pk}/modify", {
        "purpose": "Updated reason",
    }, format="json")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "modification_not_permitted"


# ============================================================================
# BR-EL-028: Early Resumption Balance Restoration
# ============================================================================

def test_early_resumption_restores_balance(stub_iam):
    _setup_employees([1001, 1003])
    _seed_balance(1001, c.EL, Decimal("10.00"))

    # User applied for 5 days: Nov 2 to Nov 6
    req = LeaveRequest.objects.create(
        user_id=1001,
        category=c.EL,
        applicant_kind="faculty",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6),
        days=Decimal("5.00"),
        purpose="Family vacation",
        status=sm.APPROVED,
        route=[
            {"step": r.UNIT_HEAD, "role": r.UNIT_HEAD},
            {"step": r.ESTABLISHMENT, "role": r.ESTABLISHMENT},
            {"step": r.SANCTION, "role": r.SANCTION},
        ],
    )
    # Approved leave had debited 5 days from ledger
    LedgerEntry.objects.create(
        user_id=1001,
        category=c.EL,
        entry_type=LedgerEntry.DEBIT,
        delta=Decimal("-5.00"),
        year=2026,
        request=req,
        note="Approved leave debit",
    )

    # User resumes early on Nov 4 (actual days taken = 3, unused = 2)
    client_applicant = _client(stub_iam, user_id=1001)
    resume_resp = client_applicant.post(
        f"/api/v1/elm/requests/{req.pk}/resume",
        {"actual_return_date": "2026-11-04", "note": "Returned 2 days early"},
        format="json",
    )
    assert resume_resp.status_code == 200

    req.refresh_from_db()
    assert req.status == sm.RESUMPTION_PENDING

    # Verifier verifies resumption
    client_verifier = _client(stub_iam, user_id=1003, active_role=r.UNIT_HEAD)
    verify_resp = client_verifier.post(
        f"/api/v1/elm/resumptions/{req.pk}/verify",
        {"verified": True, "note": "Verified return on Nov 4"},
        format="json",
    )
    assert verify_resp.status_code == 200

    req.refresh_from_db()
    assert req.status == sm.CLOSED
    assert req.days == Decimal("3.00")
    assert req.end_date == date(2026, 11, 4)

    # Check that a restore entry of +2.00 was created
    restore_entry = LedgerEntry.objects.filter(
        request=req, entry_type=LedgerEntry.RESTORE
    ).first()
    assert restore_entry is not None
    assert restore_entry.delta == Decimal("2.00")

    # Net ledger balance: 10 - 5 + 2 = 7 available
    client_check = _client(stub_iam, user_id=1001)
    bal_resp = client_check.get("/api/v1/elm/balances")
    assert Decimal(str(bal_resp.json()["available"][c.EL])) == Decimal("7.00")


# ============================================================================
# BR-EL-016..019: Workflow Decision Authority
# ============================================================================

def test_unit_head_cannot_approve_higher_sanction_leave(stub_iam):
    """BR-EL-017: Unit Head cannot approve EL directly; only recommend or not_recommend."""
    _setup_employees([1001, 1004])
    _seed_balance(1001, c.EL, Decimal("15.00"))

    req = LeaveRequest.objects.create(
        user_id=1001,
        category=c.EL,
        applicant_kind="faculty",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6),
        days=Decimal("5.00"),
        purpose="Annual leave",
        status=sm.AWAITING_UNIT_HEAD,
        current_role=r.UNIT_HEAD,
        stage=0,
        route=[
            {"step": r.UNIT_HEAD, "role": r.UNIT_HEAD},
            {"step": r.ESTABLISHMENT, "role": r.ESTABLISHMENT},
            {"step": r.SANCTION, "role": r.SANCTION},
        ],
    )

    client_uh = _client(stub_iam, user_id=1004, active_role=r.UNIT_HEAD)

    # Trying to approve EL directly must fail
    resp_approve = client_uh.post(
        f"/api/v1/elm/queue/{req.pk}/decide",
        {"event": sm.APPROVE, "note": "Premature approval"},
        format="json",
    )
    assert resp_approve.status_code == 400
    assert resp_approve.json()["error"]["code"] == "invalid_action"

    # Recommending EL succeeds and routes to Establishment
    resp_recommend = client_uh.post(
        f"/api/v1/elm/queue/{req.pk}/decide",
        {"event": sm.RECOMMEND, "note": "Recommended by HOD"},
        format="json",
    )
    assert resp_recommend.status_code == 200

    req.refresh_from_db()
    assert req.status == sm.AWAITING_ESTABLISHMENT
    assert req.current_role == r.ESTABLISHMENT
    assert req.stage == 1


# ============================================================================
# Serializer Validation Constraints
# ============================================================================

def test_serializer_validation_constraints(stub_iam):
    _setup_employees([1001])
    client = _client(stub_iam, user_id=1001)

    # 1. End date before start date
    resp1 = client.post("/api/v1/elm/requests", {
        "category": c.CL,
        "start_date": "2026-11-10",
        "end_date": "2026-11-05",
        "purpose": "Test",
    }, format="json")
    assert resp1.status_code == 400
    assert "end_date" in str(resp1.json())

    # 2. Half-day on EL (only CL allows half day)
    resp2 = client.post("/api/v1/elm/requests", {
        "category": c.EL,
        "start_date": "2026-11-10",
        "end_date": "2026-11-10",
        "half": c.FIRST_HALF,
        "purpose": "Test",
    }, format="json")
    assert resp2.status_code == 400
    assert "half" in str(resp2.json())

    # 3. Half-day spanning multiple days
    resp3 = client.post("/api/v1/elm/requests", {
        "category": c.CL,
        "start_date": "2026-11-10",
        "end_date": "2026-11-11",
        "half": c.FIRST_HALF,
        "purpose": "Test",
    }, format="json")
    assert resp3.status_code == 400
    assert "half" in str(resp3.json())

    # 4. Commuted Leave without medical evidence
    resp4 = client.post("/api/v1/elm/requests", {
        "category": c.COL,
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "purpose": "Medical issue",
        "medical_evidence": "",
    }, format="json")
    assert resp4.status_code == 400
    assert "medical_evidence" in str(resp4.json())

    # 5. Station leave missing away details
    resp5 = client.post("/api/v1/elm/requests", {
        "category": c.CL,
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "purpose": "Out of station",
        "station_leave": True,
        "station_from": "2026-11-10",
        "station_to": "",
    }, format="json")
    assert resp5.status_code == 400
    assert "station_to" in str(resp5.json())
