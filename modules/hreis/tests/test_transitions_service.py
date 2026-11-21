"""Approval routing, HR verification and balance debit are real transactions."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.principal import Principal
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequestTransition,
    LeaveLedgerEntry,
    Notification,
)
from modules.hreis.services import requests as submissions
from modules.hreis.services import transitions

pytestmark = pytest.mark.django_db


def actor(user, role, kind, perms):
    return Principal(
        user_id=user,
        username=f"user{user}",
        display_name=f"User {user}",
        kind=kind,
        active_role=role,
        roles=(role,),
        permissions=frozenset(perms),
        modules=("hreis",),
    )


def employee():
    return actor(10, "faculty", "faculty", ("hreis.leave.create", "hreis.claim.create"))


def hr():
    return actor(99, "hradmin", "staff", ("hreis.claim.review",))


def hod():
    return actor(201, "HOD (CSE)", "faculty", ("hreis.leave.approve", "hreis.claim.approve"))


def registrar():
    return actor(202, "Registrar", "staff", ("hreis.leave.approve", "hreis.claim.approve"))


@pytest.fixture(autouse=True)
def setup_employee():
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
    )


@pytest.fixture
def route():
    return [
        {"employee_kind": "faculty", "department": "CSE", "authorities": ["HOD (CSE)", "Registrar"]}
    ]


def policy(family, params):
    now = timezone.now()
    return HRPolicyVersion.objects.create(
        family=family,
        version=1,
        effective_from=now - timedelta(days=1),
        effective_until=now + timedelta(days=1),
        parameters=params,
        approved_by_user_id=99,
        approved_designation="hradmin",
    )


def leave_request(route, units="4"):
    p = policy("leave", {"routes": route, "eligibility": {"faculty": {"Casual": True}}})
    LeaveLedgerEntry.objects.create(
        user_id=10,
        leave_type="Casual",
        quantity=Decimal(units),
        policy_version=p,
        event_key="original-credit",
    )
    return submissions.submit_leave(
        employee(),
        leave_type="Casual",
        duration=Decimal("2"),
        justification="Family",
        idempotency_key="leave-original",
    )


def test_leave_requires_current_role_and_final_authority(route):
    row = leave_request(route)
    with pytest.raises(ConflictError) as exc:
        transitions.decide_request(
            hod(),
            request_id=row.id,
            event="approve",
            reason="",
            idempotency_key="premature-approval",
        )
    assert exc.value.code == "route_not_final"
    with pytest.raises(NotFoundError):
        transitions.decide_request(
            registrar(),
            request_id=row.id,
            event="forward",
            reason="",
            idempotency_key="wrong-actor",
        )
    first = transitions.decide_request(
        hod(),
        request_id=row.id,
        event="forward",
        reason="",
        idempotency_key="forward-one",
    )
    assert first.route_step == 1 and first.state == "pending_authority"
    final = transitions.decide_request(
        registrar(),
        request_id=row.id,
        event="approve",
        reason="",
        idempotency_key="approve-final",
    )
    assert final.state == "approved"
    assert sum(
        LeaveLedgerEntry.objects.filter(
            user_id=10,
            leave_type="Casual",
        ).values_list("quantity", flat=True)
    ) == Decimal("2")
    assert HRRequestTransition.objects.filter(request=row).count() == 3
    assert AuditEvent.objects.filter(resource_id=row.id, resource_kind="hr_request").count() == 3
    assert Notification.objects.filter(request=row).count() == 3


def test_request_owner_cannot_advance_their_own_leave_approval(route):
    row = leave_request(route)
    owner_acting_as_hod = actor(
        10, "HOD (CSE)", "faculty", ("hreis.leave.approve",)
    )
    with pytest.raises(NotFoundError) as exc:
        transitions.decide_request(
            owner_acting_as_hod,
            request_id=row.id,
            event="forward",
            reason="",
            idempotency_key="self-approval-attempt",
        )
    assert exc.value.code == "request_not_assigned"
    row.refresh_from_db()
    assert row.state == "pending_authority"
    assert row.route_step == 0
    assert not HRRequestTransition.objects.filter(
        request=row, event="forward"
    ).exists()


def test_reject_requires_reason_and_never_debits(route):
    row = leave_request(route)
    with pytest.raises(BadRequestError):
        transitions.decide_request(
            hod(),
            request_id=row.id,
            event="reject",
            reason="",
            idempotency_key="blank-reject",
        )
    transitions.decide_request(
        hod(),
        request_id=row.id,
        event="reject",
        reason="Not eligible",
        idempotency_key="reject",
    )
    row.refresh_from_db()
    assert row.state == "rejected"
    assert LeaveLedgerEntry.objects.count() == 1


def test_claim_hr_attestation_then_authority_route(route, monkeypatch):
    policy("ltc", {"routes": route})
    monkeypatch.setattr(
        "modules.directory.contracts.get_users",
        lambda ids: {10: SimpleNamespace(kind="faculty")},
    )
    row = submissions.submit_claim(
        employee(),
        family="ltc",
        subtype="advance",
        prescribed_form_reference="form-42",
        idempotency_key="claim-init",
    )
    owner_acting_as_hr = actor(10, "hradmin", "faculty", ("hreis.claim.review",))
    with pytest.raises(NotFoundError) as exc:
        transitions.verify_claim(
            owner_acting_as_hr,
            request_id=row.id,
            document_review_reference="signed-form-42",
            eligibility_basis="Independent verification required",
            idempotency_key="self-verification-attempt",
        )
    assert exc.value.code == "claim_not_assigned"
    with pytest.raises(BadRequestError):
        transitions.verify_claim(
            hr(),
            request_id=row.id,
            document_review_reference="",
            eligibility_basis="Inspected",
            idempotency_key="incomplete-review",
        )
    verified = transitions.verify_claim(
        hr(),
        request_id=row.id,
        document_review_reference="signed-form-42",
        eligibility_basis="Institutional eligibility evidence",
        idempotency_key="verified-review",
    )
    assert verified.state == "pending_authority"
    assert verified.claim.hr_verified_by_user_id == 99
    transitions.decide_request(
        hod(),
        request_id=row.id,
        event="forward",
        reason="",
        idempotency_key="forward-claim",
    )
    final = transitions.decide_request(
        registrar(),
        request_id=row.id,
        event="approve",
        reason="",
        idempotency_key="approve-claim",
    )
    assert final.state == "approved"
    assert final.claim.financial_verified_by_user_id is None
