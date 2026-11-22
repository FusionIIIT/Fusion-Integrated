from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.hreis.domain.state_machine import PENDING_NEXT_AUTHORITY
from modules.hreis.models import EmployeeServiceRecord, HRPolicyVersion, LeaveBalanceEntry
from modules.hreis.services.requests import (
    adjust_leave_balance,
    create_request,
    transition_request,
)


def actor(user_id, role, permissions):
    permissions = frozenset(permissions)
    return SimpleNamespace(
        user_id=user_id,
        active_role=role,
        permissions=permissions,
        has_permission=lambda code: code in permissions,
    )


@pytest.mark.django_db
def test_leave_request_moves_through_configured_route_and_deducts_once():
    EmployeeServiceRecord.objects.create(user_id=10, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={
            "approval_routes": {"leave": {"faculty": ["HOD (CSE)", "Director"]}},
            "eligible_leave_types": {"faculty": ["earned"]},
        },
    )
    hr_admin = actor(20, "hradmin", {"hreis.leave_balance.manage"})
    adjust_leave_balance(
        actor=hr_admin,
        user_id=10,
        leave_type="earned",
        delta_days="5",
        reason="Opening balance",
    )
    employee = actor(10, "faculty", {"hreis.request.create"})
    request = create_request(
        actor=employee,
        request_type="leave",
        data={"leave_type": "earned", "duration_days": "2", "justification": "Personal leave"},
        idempotency_key="create-leave-10",
    )
    assert request.state == "pending_current_authority"
    assert request.current_authority_designation == "HOD (CSE)"

    hod = actor(21, "HOD (CSE)", {"hreis.request.review"})
    request = transition_request(
        request_id=request.pk, actor=hod, event="forward", idempotency_key="forward-hod-10"
    )
    assert request.state == PENDING_NEXT_AUTHORITY
    assert request.current_authority_designation == "Director"

    director = actor(22, "Director", {"hreis.request.review"})
    request = transition_request(
        request_id=request.pk, actor=director, event="approve", idempotency_key="approve-dir-10"
    )
    replay = transition_request(
        request_id=request.pk, actor=director, event="approve", idempotency_key="approve-dir-10"
    )
    assert replay.pk == request.pk
    assert request.state == "approved_leave_balance_updated"
    assert LeaveBalanceEntry.objects.filter(request=request).count() == 1
    balance = sum(
        LeaveBalanceEntry.objects.filter(user_id=10, leave_type="earned").values_list(
            "delta_days", flat=True
        )
    )
    assert balance == Decimal("3")


@pytest.mark.django_db
def test_request_creation_fails_actionably_without_policy():
    EmployeeServiceRecord.objects.create(user_id=11, employee_category="faculty")
    employee = actor(11, "faculty", {"hreis.request.create"})
    with pytest.raises(BadRequestError, match="policy is not configured"):
        create_request(
            actor=employee,
            request_type="leave",
            data={"leave_type": "earned", "duration_days": "1", "justification": "Personal leave"},
            idempotency_key="create-leave-11",
        )


@pytest.mark.django_db
def test_request_creation_is_idempotent_and_rejects_key_reuse():
    EmployeeServiceRecord.objects.create(user_id=13, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={
            "approval_routes": {"leave": {"faculty": ["HOD (CSE)"]}},
            "eligible_leave_types": {"faculty": ["earned"]},
        },
    )
    adjust_leave_balance(
        actor=actor(20, "hradmin", {"hreis.leave_balance.manage"}),
        user_id=13,
        leave_type="earned",
        delta_days="4",
        reason="Opening balance",
    )
    employee = actor(13, "faculty", {"hreis.request.create"})
    payload = {"leave_type": "earned", "duration_days": "1", "justification": "Personal"}
    first = create_request(
        actor=employee, request_type="leave", data=payload, idempotency_key="stable-key-13"
    )
    replay = create_request(
        actor=employee, request_type="leave", data=payload, idempotency_key="stable-key-13"
    )
    assert replay.pk == first.pk
    with pytest.raises(ConflictError, match="already used"):
        create_request(
            actor=employee,
            request_type="leave",
            data={**payload, "duration_days": "2"},
            idempotency_key="stable-key-13",
        )


@pytest.mark.django_db
def test_leave_balance_adjustment_cannot_make_balance_negative():
    EmployeeServiceRecord.objects.create(user_id=14, employee_category="faculty")
    hr_admin = actor(20, "hradmin", {"hreis.leave_balance.manage"})
    with pytest.raises(BadRequestError, match="below zero"):
        adjust_leave_balance(
            actor=hr_admin,
            user_id=14,
            leave_type="earned",
            delta_days="-1",
            reason="Correction",
        )


@pytest.mark.django_db
def test_appraisal_route_supports_multiple_configured_authorities(monkeypatch):
    EmployeeServiceRecord.objects.create(user_id=12, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={
            "approval_routes": {
                "appraisal": {"faculty": ["HOD (CSE)", "Registrar", "Director"]},
            },
            "appraisal_windows": {
                "2026": {"opens": date.today().isoformat(), "closes": date.today().isoformat()},
            },
        },
    )
    employee = actor(12, "faculty", {"hreis.request.create"})
    monkeypatch.setattr(
        "modules.hreis.services.requests.get_users",
        lambda user_ids: {user_id: SimpleNamespace(kind="faculty") for user_id in user_ids},
    )
    appraisal = create_request(
        actor=employee,
        request_type="appraisal",
        data={"cycle_key": "2026"},
        idempotency_key="create-appraisal-12",
    )
    hr = actor(30, "hradmin", {"hreis.request.assign"})
    appraisal = transition_request(
        request_id=appraisal.pk,
        actor=hr,
        event="assign_reviewers",
        details={"reviewer_user_ids": [31]},
        idempotency_key="assign-reviewers-12",
    )
    for index, authority in enumerate(("HOD (CSE)", "Registrar")):
        reviewer = actor(40 + index, authority, {"hreis.request.review"})
        appraisal = transition_request(
            request_id=appraisal.pk,
            actor=reviewer,
            event="forward",
            idempotency_key=f"forward-{authority.lower()}-12",
        )
    assert appraisal.current_authority_designation == "Director"
    director = actor(50, "Director", {"hreis.request.review"})
    appraisal = transition_request(
        request_id=appraisal.pk,
        actor=director,
        event="finalize",
        idempotency_key="finalize-appraisal-12",
    )
    assert appraisal.state == "finalized_archived_closed"
