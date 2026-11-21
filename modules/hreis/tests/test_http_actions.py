"""HTTP smoke tests for HR-EIS writes with the actual DRF permission stack."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    LeaveLedgerEntry,
    Notification,
    OutboxEvent,
)
from modules.hreis.services import notifications as email_service

pytestmark = pytest.mark.django_db


def client_for(stub_iam, *, user_id=10, role="faculty", kind="faculty", permissions=(), users=None):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=role,
            roles=(role,),
            permissions=permissions,
            modules=("hreis",),
        ),
        users=users or {},
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return client


def policy(family, parameters):
    now = timezone.now()
    return HRPolicyVersion.objects.create(
        family=family,
        version=1,
        effective_from=now - timedelta(hours=2),
        effective_until=now + timedelta(hours=2),
        parameters=parameters,
        approved_by_user_id=99,
        approved_designation="hradmin",
    )


def employee():
    return EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
        service_history=[],
    )


def test_leave_http_creates_audited_request_without_premature_debit(stub_iam, monkeypatch):
    # HR-CFR-002, HR-AFR-002, HR-AFR-029, HR-AFR-036,
    # HR-AFR-041, HR-AFR-077, HR-AFR-083, BR-HR-007,
    # CW-HR-01: submitted request is accepted with independent audit and mail.
    employee()
    p = policy(
        "leave",
        {
            "eligibility": {"faculty": {"Casual": True}},
            "routes": [
                {
                    "employee_kind": "faculty",
                    "department": "CSE",
                    "authorities": ["HOD (CSE)", "Registrar"],
                }
            ],
        },
    )
    LeaveLedgerEntry.objects.create(
        user_id=10,
        leave_type="Casual",
        quantity=Decimal("5"),
        event_key="verified-initial",
        policy_version=p,
    )
    c = client_for(stub_iam, permissions=("hreis.leave.create", "hreis.request.view"))
    params = {"leave_type": "Casual", "duration": "2", "justification": "Family"}
    response = c.post(
        "/api/v1/hreis/requests/leave/", params, format="json", HTTP_IDEMPOTENCY_KEY="http-leave-1"
    )
    assert response.status_code == 201, response.content
    row = HRRequest.objects.get(pk=response.json()["id"])
    assert row.user_id == 10 and row.state == "pending_authority"
    assert row.payload == {"duration": "2.0000", "justification": "Family"}
    assert AuditEvent.objects.get(event_key="request:http-leave-1").subject_user_id == 10
    assert Notification.objects.filter(request=row).count() == 1
    outbound = OutboxEvent.objects.get(event_key="outbox:http-leave-1")
    assert outbound.event_type == "hreis.notification"
    monkeypatch.setattr(
        email_service, "get_users",
        lambda ids: {10: SimpleNamespace(email="employee@example.edu", is_active=True)},
    )
    with patch.object(email_service, "send_mail", return_value=1) as mail:
        assert email_service.deliver_pending_notifications() == (1, 0)
    assert mail.call_args.kwargs["recipient_list"] == ["employee@example.edu"]
    outbound.refresh_from_db()
    assert outbound.dispatched_at is not None
    assert LeaveLedgerEntry.objects.count() == 1
    replay = c.post(
        "/api/v1/hreis/requests/leave/", params, format="json", HTTP_IDEMPOTENCY_KEY="http-leave-1"
    )
    assert replay.status_code == 409
    assert c.get("/api/v1/hreis/requests/").json()["results"][0]["id"] == row.id


def test_policy_creation_http_rejects_wrong_role_and_records_version(stub_iam):
    # HR-UC-017, HR-AFR-012, BR-HR-029: HR may publish explicit version;
    # an unassigned ordinary faculty cannot impersonate the HR administrator.
    now = timezone.now()
    params = {
        "family": "leave",
        "version": 1,
        "effective_from": (now - timedelta(hours=1)).isoformat(),
        "effective_until": (now + timedelta(hours=1)).isoformat(),
        "parameters": {"conditions": {"requires_verification": True}},
    }
    unauthorized = client_for(
        stub_iam,
        role="faculty",
        permissions=("hreis.policy.manage",),
    )
    assert (
        unauthorized.post(
            "/api/v1/hreis/policies/", params, format="json", HTTP_IDEMPOTENCY_KEY="denied"
        ).status_code
        == 403
    )
    admin = client_for(
        stub_iam,
        user_id=99,
        role="hradmin",
        kind="staff",
        permissions=("hreis.policy.manage", "hreis.policy.view"),
    )
    response = admin.post(
        "/api/v1/hreis/policies/", params, format="json", HTTP_IDEMPOTENCY_KEY="http-policy-1"
    )
    assert response.status_code == 201, response.content
    assert response.json()["family"] == "leave"
    assert HRPolicyVersion.objects.count() == 1
    assert admin.get("/api/v1/hreis/policies/").status_code == 200
    assert AuditEvent.objects.filter(event_key="policy:http-policy-1").exists()


def test_claim_http_requires_real_hr_verification_before_approval(stub_iam, user_ref):
    # HR-AFR-011, HR-AFR-052, HR-AFR-053, HR-AFR-065,
    # BR-HR-017, BR-HR-021: HR attestation follows inspected evidence.
    employee()
    policy(
        "ltc",
        {
            "conditions": {"requires_hr_verification": True},
            "routes": [
                {"employee_kind": "faculty", "department": "CSE", "authorities": ["Registrar"]}
            ],
        },
    )
    c = client_for(stub_iam, permissions=("hreis.claim.create",))
    submitted = c.post(
        "/api/v1/hreis/requests/claims/",
        {
            "family": "ltc",
            "subtype": "advance",
            "prescribed_form_reference": "approved-form-1",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="http-ltc-1",
    )
    assert submitted.status_code == 201, submitted.content
    request_id = submitted.json()["id"]
    assert submitted.json()["state"] == "awaiting_hr_verification"
    admin = client_for(
        stub_iam,
        user_id=99,
        role="hradmin",
        kind="staff",
        permissions=("hreis.claim.review",),
        users={10: user_ref(10, "Faculty Ten", kind="faculty")},
    )
    endpoint = f"/api/v1/hreis/requests/{request_id}/verify-claim/"
    missing = admin.post(
        endpoint,
        {
            "document_review_reference": "",
            "eligibility_basis": "Verified",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="http-ltc-no-evidence",
    )
    assert missing.status_code == 400
    verified = admin.post(
        endpoint,
        {
            "document_review_reference": "review-log-1",
            "eligibility_basis": "Manual eligibility review",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="http-ltc-verify",
    )
    assert verified.status_code == 200, verified.content
    assert verified.json()["state"] == "pending_authority"
    assert HRRequest.objects.get(pk=request_id).claim.hr_verified_by_user_id == 99
