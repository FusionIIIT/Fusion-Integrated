"""Verified leave credit workflow: HR may enter evidence-backed amounts, never default quotas."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    LeaveLedgerEntry,
)

pytestmark = pytest.mark.django_db
URL = "/api/v1/hreis/leave-balances/credits/"


@pytest.fixture
def source(user_ref):
    EmployeeServiceRecord.objects.create(
        user_id=10,
        appointment_details={"joined": "2026-01-01"},
        department="CSE",
        designation_snapshot="Professor",
        service_history=[],
    )
    now = timezone.now()
    policy = HRPolicyVersion.objects.create(
        family="leave", version=1, effective_from=now - timedelta(days=1),
        parameters={"eligibility": {"faculty": {"Casual": True, "Medical": False}}},
        approved_by_user_id=99, approved_designation="hradmin",
    )
    return {10: user_ref(10, "Employee Ten", kind="faculty")}, policy


def client(stub_iam, *, role="hradmin", user_id=99, permissions=("hreis.balance.manage",), users=None):
    stub_iam(make_session(
        user_id=user_id, kind="staff", active_role=role, roles=(role,),
        permissions=permissions, modules=("hreis",),
    ), users=users)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return c


def payload():
    return {
        "user_id": 10,
        "leave_type": "Casual",
        "quantity": "4.5",
        "evidence_reference": "signed-leave-register-page-25",
    }


def test_hr_afr_024_036_credits_are_verified_and_audited(stub_iam, source):
    # HR-CFR-006/007, HR-AFR-024/036; never invent a quota or alter the old ledger.
    users, policy = source
    c = client(stub_iam, users=users)
    created = c.post(URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="manual-credit-1")
    assert created.status_code == 201, created.content
    assert created.json()["user_id"] == 10
    assert Decimal(created.json()["quantity"]) == Decimal("4.5")
    entry = LeaveLedgerEntry.objects.get()
    assert entry.policy_version_id == policy.pk
    assert entry.actor_user_id == 99
    event = AuditEvent.objects.get()
    assert event.action == "leave_balance_credit"
    assert event.data["evidence_reference"] == "signed-leave-register-page-25"
    employee = client(
        stub_iam, role="faculty", user_id=10,
        permissions=("hreis.service_record.view",), users=users,
    )
    record = employee.get("/api/v1/hreis/service-records/me/")
    assert record.status_code == 200
    assert Decimal(record.json()["leave_balances"]["Casual"]) == Decimal("4.5")


def test_unauthorized_and_self_credit_denied(stub_iam, source):
    users, _ = source
    staff = client(stub_iam, role="staff", user_id=10, users=users)
    assert staff.post(
        URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="role-bypass",
    ).status_code == 403
    self_admin = client(stub_iam, user_id=10, users=users)
    assert self_admin.post(
        URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="self-credit",
    ).status_code == 404
    administrator = client(stub_iam, permissions=(), users=users)
    assert administrator.post(
        URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="no-grant",
    ).status_code == 403
    assert not LeaveLedgerEntry.objects.exists()


def test_replay_and_invalid_evidence_never_credit_twice(stub_iam, source):
    users, _ = source
    c = client(stub_iam, users=users)
    first = c.post(URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="manual-credit-1")
    assert first.status_code == 201, first.content
    again = c.post(URL, payload(), format="json", HTTP_IDEMPOTENCY_KEY="manual-credit-1")
    assert again.status_code == 409
    for idx, item in enumerate([
        {**payload(), "quantity": "-3"},
        {**payload(), "evidence_reference": ""},
        {**payload(), "leave_type": "Medical"},
        {**payload(), "leave_type": "Other"},
        {**payload(), "user_id": 100},
    ]):
        response = c.post(URL, item, format="json", HTTP_IDEMPOTENCY_KEY=f"invalid-{idx}")
        assert response.status_code in {400, 404, 409}, response.content
    assert LeaveLedgerEntry.objects.count() == 1
    assert AuditEvent.objects.count() == 1
