from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.hreis.models import AuditEvent, EmployeeServiceRecord, HRRequest
from modules.hreis.services.requests import (
    adjust_leave_balance,
    create_policy_version,
    maintain_employee_record,
    transition_request,
)

pytestmark = pytest.mark.django_db


def actor(user_id, permissions=(), role="hradmin"):
    permissions = frozenset(permissions)
    return SimpleNamespace(
        user_id=user_id,
        active_role=role,
        has_permission=lambda code: code in permissions,
    )


def test_service_record_authorization_and_validation():
    with pytest.raises(PermissionDeniedError):
        maintain_employee_record(actor=actor(1), user_id=2, values={"employee_category": "faculty"})
    admin = actor(1, {"hreis.employee.manage"})
    with pytest.raises(BadRequestError, match="cannot be changed"):
        maintain_employee_record(actor=admin, user_id=2, values={"user_id": 4})
    with pytest.raises(BadRequestError, match="at least one"):
        maintain_employee_record(actor=admin, user_id=2, values={})
    with pytest.raises(BadRequestError, match="employee category"):
        maintain_employee_record(actor=admin, user_id=2, values={"department_code": "CSE"})
    record = maintain_employee_record(
        actor=admin,
        user_id=2,
        values={"employee_category": "faculty", "department_code": "CSE"},
    )
    updated = maintain_employee_record(actor=admin, user_id=2, values={"designation": "Professor"})
    assert updated.pk == record.pk
    assert updated.updated_by_user_id == 1
    assert AuditEvent.objects.filter(action="employee_record_updated").count() == 2


def test_policy_creation_is_immutable_and_rejects_bad_dates():
    admin = actor(1, {"hreis.policy.manage"})
    values = {
        "policy_name": "hr",
        "version": 1,
        "effective_from": date.today(),
        "effective_to": date.today(),
        "payload": {"approval_routes": {}},
    }
    with pytest.raises(PermissionDeniedError):
        create_policy_version(actor=actor(2), **values)
    with pytest.raises(BadRequestError, match="non-empty"):
        create_policy_version(actor=admin, **{**values, "payload": {}})
    with pytest.raises(BadRequestError, match="end date"):
        create_policy_version(
            actor=admin,
            policy_name="invalid",
            version=1,
            effective_from=date.today(),
            effective_to=date.today() - timedelta(days=1),
            payload={"x": 1},
        )
    policy = create_policy_version(actor=admin, **values)
    with pytest.raises(ValidationError, match="immutable"):
        policy.save()
    with pytest.raises(ValidationError, match="cannot be deleted"):
        policy.delete()
    with pytest.raises(ConflictError, match="already exists"):
        create_policy_version(actor=admin, **values)
    with pytest.raises(BadRequestError, match="retroactively"):
        create_policy_version(
            actor=admin,
            policy_name="old",
            version=1,
            effective_from=date.today() - timedelta(days=1),
            effective_to=None,
            payload={"x": 1},
        )
    with pytest.raises(ConflictError, match="overlap"):
        create_policy_version(
            actor=admin,
            policy_name="hr",
            version=2,
            effective_from=date.today(),
            effective_to=None,
            payload={"x": 1},
        )


def test_balance_adjustment_validation_and_audit():
    admin = actor(1, {"hreis.leave_balance.manage"})
    with pytest.raises(PermissionDeniedError):
        adjust_leave_balance(
            actor=actor(2), user_id=3, leave_type="earned", delta_days="1", reason="opening"
        )
    with pytest.raises(BadRequestError, match="valid balance adjustment"):
        adjust_leave_balance(
            actor=admin, user_id=3, leave_type="earned", delta_days="bad", reason="opening"
        )
    with pytest.raises(BadRequestError, match="non-zero"):
        adjust_leave_balance(
            actor=admin, user_id=3, leave_type="earned", delta_days="NaN", reason="opening"
        )
    with pytest.raises(BadRequestError, match="non-zero"):
        adjust_leave_balance(
            actor=admin, user_id=3, leave_type="earned", delta_days="0", reason="opening"
        )
    with pytest.raises(BadRequestError, match="non-zero"):
        adjust_leave_balance(
            actor=admin, user_id=3, leave_type="other", delta_days="1", reason="opening"
        )
    with pytest.raises(BadRequestError, match="non-zero"):
        adjust_leave_balance(
            actor=admin, user_id=3, leave_type="earned", delta_days="1", reason=" "
        )
    with pytest.raises(BadRequestError, match="service record"):
        adjust_leave_balance(
            actor=admin, user_id=3, leave_type="earned", delta_days="1", reason="opening"
        )
    EmployeeServiceRecord.objects.create(user_id=3, employee_category="faculty")
    entry = adjust_leave_balance(
        actor=admin, user_id=3, leave_type="earned", delta_days="2", reason="Opening balance"
    )
    assert entry.delta_days == 2
    assert AuditEvent.objects.filter(action="leave_balance_adjusted").count() == 1


def test_transition_replay_conflict_permission_and_missing_request():
    with pytest.raises(BadRequestError, match="Idempotency-Key"):
        transition_request(request_id=1, actor=actor(1), event="approve", idempotency_key="short")
    with pytest.raises(NotFoundError):
        transition_request(
            request_id=1,
            actor=actor(1),
            event="approve",
            idempotency_key="not-found-1",
        )
    request = HRRequest.objects.create(
        owner_user_id=10,
        request_type="leave",
        state="pending_current_authority",
        approval_route=["HOD (CSE)"],
        current_authority_designation="HOD (CSE)",
    )
    with pytest.raises(PermissionDeniedError):
        transition_request(
            request_id=request.pk,
            actor=actor(11),
            event="approve",
            idempotency_key="denied-approval-11",
        )
