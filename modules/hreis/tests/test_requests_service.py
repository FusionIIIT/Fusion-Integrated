"""Real API service checks for employee HR requests."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.hreis.models import (
    AppraisalDetail,
    ApprovalRouteStep,
    AuditEvent,
    ClaimDetail,
    ClaimDocument,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    HRRequestTransition,
    LeaveLedgerEntry,
    Notification,
    OutboxEvent,
)
from modules.hreis.services import requests as service

pytestmark = pytest.mark.django_db


def actor(kind="faculty", grants=None):
    return Principal(
        user_id=10,
        username="employee10",
        display_name="Employee",
        kind=kind,
        active_role=kind,
        roles=(kind,),
        permissions=frozenset(
            grants
            if grants is not None
            else ("hreis.leave.create", "hreis.claim.create", "hreis.appraisal.create")
        ),
        modules=("hreis",),
    )


@pytest.fixture(autouse=True)
def employee():
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
        service_history=[],
    )


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


def route():
    return [
        {"employee_kind": "faculty", "department": "CSE", "authorities": ["HOD (CSE)", "Registrar"]}
    ]


def credit(policy_row):
    return LeaveLedgerEntry.objects.create(
        user_id=10,
        leave_type="Casual",
        quantity=Decimal("8"),
        policy_version=policy_row,
        event_key="verified-opening-balance",
    )


def test_leave_requires_explicit_config_and_trusted_ledger():
    with pytest.raises(ConflictError) as exc:
        service.submit_leave(
            actor(),
            leave_type="Casual",
            duration=Decimal("2"),
            justification="Family event",
            idempotency_key="no-policy",
        )
    assert exc.value.code == "policy_unavailable"
    p = policy("leave", {"routes": route(), "eligibility": {"faculty": {"Casual": True}}})
    with pytest.raises(ConflictError) as exc:
        service.submit_leave(
            actor(),
            leave_type="Casual",
            duration=Decimal("2"),
            justification="Family event",
            idempotency_key="no-balance",
        )
    assert exc.value.code == "insufficient_balance"
    credit(p)
    row = service.submit_leave(
        actor(),
        leave_type="Casual",
        duration=Decimal("2"),
        justification="Family event",
        idempotency_key="leave-submit",
    )
    assert row.user_id == 10 and row.state == "pending_authority"
    assert row.policy_version_id == p.pk
    assert row.payload["duration"] == "2"
    assert list(
        ApprovalRouteStep.objects.filter(request=row).values_list("designation", flat=True)
    ) == ["HOD (CSE)", "Registrar"]
    assert HRRequestTransition.objects.get(request=row).specification == "CW-HR-01"
    assert AuditEvent.objects.get(event_key="request:leave-submit").actor_user_id == 10
    assert Notification.objects.get(event_key="notification:leave-submit").recipient_user_id == 10
    assert OutboxEvent.objects.get(event_key="outbox:leave-submit").dispatched_at is None
    assert LeaveLedgerEntry.objects.count() == 1


def test_request_replay_and_role_denial_do_not_mutate():
    p = policy("leave", {"routes": route(), "eligibility": {"faculty": {"Casual": True}}})
    credit(p)
    kwargs = {
        "leave_type": "Casual",
        "duration": Decimal("1"),
        "justification": "Medical appointment",
        "idempotency_key": "same-key",
    }
    service.submit_leave(actor(), **kwargs)
    with pytest.raises(ConflictError) as exc:
        service.submit_leave(actor(), **kwargs)
    assert exc.value.code == "operation_replayed"
    with pytest.raises(PermissionDeniedError):
        service.submit_leave(actor(grants=()), **{**kwargs, "idempotency_key": "denied"})
    assert HRRequest.objects.count() == 1


def test_claim_submission_unverified_is_not_misrepresented_as_verified():
    policy("ltc", {"conditions": {"requires_hr_verification": True}})
    row = service.submit_claim(
        actor(),
        family="ltc",
        subtype="advance",
        prescribed_form_reference="official-form-reference",
        idempotency_key="ltc-create",
    )
    assert row.state == "awaiting_hr_verification"
    assert (
        ClaimDetail.objects.get(request=row).prescribed_form_reference == "official-form-reference"
    )
    assert not ClaimDocument.objects.exists()
    assert not ApprovalRouteStep.objects.exists()


def test_cpda_requires_supporting_information_and_records_only_pending():
    policy("cpda", {"conditions": {"requires_hr_verification": True}})
    with pytest.raises(BadRequestError) as exc:
        service.submit_claim(
            actor(),
            family="cpda",
            subtype="reimbursement",
            purpose="Training",
            amount=Decimal("120.25"),
            idempotency_key="missing-doc",
        )
    assert exc.value.code == "missing_documents"
    row = service.submit_claim(
        actor(),
        family="cpda",
        subtype="reimbursement",
        purpose="Training",
        amount=Decimal("120.25"),
        document_references=["opaque-ref-1"],
        idempotency_key="cpda-create",
    )
    assert row.state == "awaiting_hr_verification"
    assert row.payload == {"document_references": ["opaque-ref-1"]}
    assert ClaimDetail.objects.get(request=row).amount == Decimal("120.25")
    assert not ClaimDocument.objects.exists()


def test_appraisal_window_required_and_period_unique():
    now = timezone.now()
    policy(
        "appraisal",
        {
            "submission_window": {
                "start": (now - timedelta(days=1)).isoformat(),
                "end": (now + timedelta(days=1)).isoformat(),
            }
        },
    )
    row = service.submit_appraisal(
        actor(),
        period_key="2026",
        submitted_form={"self_rating": "Met"},
        idempotency_key="appraisal-submit",
    )
    assert row.state == "submitted"
    assert AppraisalDetail.objects.get(request=row).submitted_form == {"self_rating": "Met"}
    with pytest.raises(ConflictError) as exc:
        service.submit_appraisal(
            actor(),
            period_key="2026",
            submitted_form={"other": "value"},
            idempotency_key="appraisal-duplicate",
        )
    assert exc.value.code == "appraisal_already_submitted"


def test_atomic_rollback_if_audit_or_notification_fails(monkeypatch):
    policy("ltc", {"conditions": {"requires_hr_verification": True}})

    def broken(*args, **kwargs):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr(service.OutboxEvent.objects, "create", broken)
    with pytest.raises(RuntimeError, match="outbox unavailable"):
        service.submit_claim(
            actor(),
            family="ltc",
            subtype="advance",
            prescribed_form_reference="form-1",
            idempotency_key="rollback",
        )
    assert not HRRequest.objects.exists()
    assert not HRRequestTransition.objects.exists()
    assert not AuditEvent.objects.exists()
    assert not Notification.objects.exists()
