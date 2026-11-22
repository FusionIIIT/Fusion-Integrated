from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.hreis.models import EmployeeServiceRecord, HRPolicyVersion
from modules.hreis.services.requests import create_request, transition_request

pytestmark = pytest.mark.django_db


def actor(user_id, role, permissions):
    permissions = frozenset(permissions)
    return SimpleNamespace(
        user_id=user_id,
        active_role=role,
        has_permission=lambda code: code in permissions,
    )


@pytest.mark.parametrize(
    ("request_type", "data", "approved_state"),
    [
        (
            "ltc_advance",
            {"form_data": {"travel": "official"}, "supporting_documents": ["doc-ref"]},
            "approved_ltc_claim",
        ),
        (
            "cpda_advance",
            {"amount": "250", "purpose": "Conference", "supporting_documents": ["doc-ref"]},
            "approved_cpda_claim",
        ),
    ],
)
def test_claims_verify_route_approve_and_record_financial_status(
    request_type, data, approved_state
):
    EmployeeServiceRecord.objects.create(user_id=61, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={"approval_routes": {request_type: {"faculty": ["HOD (CSE)"]}}},
    )
    request = create_request(
        actor=actor(61, "faculty", {"hreis.request.create"}),
        request_type=request_type,
        data=data,
        idempotency_key=f"create-{request_type}-61",
    )
    hr = actor(90, "hradmin", {"hreis.request.manage"})
    request = transition_request(
        request_id=request.pk,
        actor=hr,
        event="verify",
        details={"checked": True},
        idempotency_key=f"verify-{request_type}-61",
    )
    assert request.state == "pending_current_authority"
    authority = actor(62, "HOD (CSE)", {"hreis.request.review"})
    request = transition_request(
        request_id=request.pk,
        actor=authority,
        event="approve",
        idempotency_key=f"approve-{request_type}-61",
    )
    assert request.state == approved_state
    accountant = actor(63, "Accounts Admin", {"hreis.claim.update"})
    with pytest.raises(BadRequestError, match="financial status"):
        transition_request(
            request_id=request.pk,
            actor=accountant,
            event="process",
            idempotency_key=f"process-empty-{request_type}-61",
        )
    request = transition_request(
        request_id=request.pk,
        actor=accountant,
        event="process",
        details={"financial_status": "paid"},
        idempotency_key=f"process-{request_type}-61",
    )
    assert request.state == "processed_financial_status_recorded"
    assert request.data["financial_processing"]["financial_status"] == "paid"


def test_only_hradmin_can_verify_claims():
    EmployeeServiceRecord.objects.create(user_id=70, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={"approval_routes": {"ltc_advance": {"faculty": ["HOD (CSE)"]}}},
    )
    request = create_request(
        actor=actor(
            70,
            "faculty",
            {"hreis.request.create"},
        ),
        request_type="ltc_advance",
        data={"form_data": {"trip": "x"}, "supporting_documents": ["doc"]},
        idempotency_key="create-ltc-70",
    )
    reviewer = actor(71, "SectionHead_HR", {"hreis.request.review"})
    with pytest.raises(PermissionDeniedError):
        transition_request(
            request_id=request.pk,
            actor=reviewer,
            event="verify",
            idempotency_key="verify-ltc-70",
        )


def test_only_existing_staff_reviewer_can_be_assigned(monkeypatch):
    EmployeeServiceRecord.objects.create(user_id=72, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={
            "approval_routes": {"appraisal": {"faculty": ["HOD (CSE)"]}},
            "appraisal_windows": {
                "2026": {"opens": date.today().isoformat(), "closes": date.today().isoformat()}
            },
        },
    )
    request = create_request(
        actor=actor(72, "faculty", {"hreis.request.create"}),
        request_type="appraisal",
        data={"cycle_key": "2026"},
        idempotency_key="create-appraisal-72",
    )
    admin = actor(90, "hradmin", {"hreis.request.assign"})
    monkeypatch.setattr("modules.hreis.services.requests.get_users", lambda ids: {})
    with pytest.raises(BadRequestError, match="existing faculty or staff"):
        transition_request(
            request_id=request.pk,
            actor=admin,
            event="assign_reviewers",
            details={"reviewer_user_ids": [73]},
            idempotency_key="assign-missing-reviewer-72",
        )
    monkeypatch.setattr(
        "modules.hreis.services.requests.get_users",
        lambda ids: {73: SimpleNamespace(kind="student")},
    )
    with pytest.raises(BadRequestError, match="existing faculty or staff"):
        transition_request(
            request_id=request.pk,
            actor=admin,
            event="assign_reviewers",
            details={"reviewer_user_ids": [73]},
            idempotency_key="assign-student-reviewer-72",
        )
    with pytest.raises(BadRequestError, match="reviewer"):
        transition_request(
            request_id=request.pk,
            actor=admin,
            event="assign_reviewers",
            details={"reviewer_user_ids": [72]},
            idempotency_key="assign-owner-reviewer-72",
        )
    with pytest.raises(BadRequestError, match="reviewer"):
        transition_request(
            request_id=request.pk,
            actor=admin,
            event="assign_reviewers",
            details={"reviewer_user_ids": [True]},
            idempotency_key="assign-boolean-reviewer-72",
        )
