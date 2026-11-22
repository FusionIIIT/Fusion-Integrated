from datetime import date
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    LeaveBalanceEntry,
    NotificationRecord,
    RequestDecision,
)
from modules.hreis.selectors import scoping

pytestmark = pytest.mark.django_db


def principal(user_id, permissions=(), role="faculty"):
    permissions = frozenset(permissions)
    return SimpleNamespace(
        user_id=user_id,
        active_role=role,
        has_permission=lambda code: code in permissions,
    )


def test_selectors_fail_closed_and_scope_to_owner_or_current_authority():
    EmployeeServiceRecord.objects.create(user_id=1, employee_category="faculty")
    EmployeeServiceRecord.objects.create(user_id=2, employee_category="staff")
    own = HRRequest.objects.create(owner_user_id=1, request_type="leave")
    assigned = HRRequest.objects.create(
        owner_user_id=2,
        request_type="leave",
        current_authority_designation="HOD (CSE)",
    )
    NotificationRecord.objects.create(user_id=1, topic="own")
    AuditEvent.objects.create(
        user_id=1,
        actor_user_id=3,
        action="saved",
        resource_type="hr_request",
        resource_id=own.pk,
    )
    assert not scoping.employee_record_for(None).exists()
    assert not scoping.requests_for(None).exists()
    assert not scoping.notifications_for(None).exists()
    assert not scoping.audit_events_for(None).exists()
    assert list(scoping.employee_record_for(principal(1)).values_list("user_id", flat=True)) == [1]
    assert set(scoping.requests_for(principal(1)).values_list("pk", flat=True)) == {own.pk}
    assert set(
        scoping.requests_for(principal(9, role="HOD (CSE)")).values_list("pk", flat=True)
    ) == {assigned.pk}
    assert list(scoping.notifications_for(principal(1)).values_list("topic", flat=True)) == ["own"]
    assert not scoping.audit_events_for(principal(1)).exists()
    assert scoping.audit_events_for(principal(1, ("hreis.audit.view",))).count() == 1
    assert scoping.employee_record_for(principal(9, ("hreis.employee.manage",))).count() == 2
    assert scoping.requests_for(principal(9, ("hreis.request.manage",))).count() == 2


def test_immutable_records_reject_updates_and_deletes():
    policy = HRPolicyVersion.objects.create(
        policy_name="hr", version=1, effective_from=date.today(), payload={"x": 1}
    )
    request = HRRequest.objects.create(owner_user_id=1, request_type="leave")
    decision = RequestDecision.objects.create(
        request=request,
        from_state="draft",
        event="submit",
        to_state="pending_current_authority",
        actor_user_id=1,
        idempotency_key="immutable-decision",
    )
    balance = LeaveBalanceEntry.objects.create(
        user_id=1,
        leave_type="earned",
        delta_days="1",
        reason="Opening",
        actor_user_id=1,
    )
    audit = AuditEvent.objects.create(
        user_id=1,
        actor_user_id=1,
        action="test",
        resource_type="request",
        resource_id=request.pk,
    )
    for row in (policy, decision, balance, audit):
        with pytest.raises(ValidationError):
            row.save()
        with pytest.raises(ValidationError):
            row.delete()


def test_record_string_representations_are_safe_and_use_internal_ids():
    employee = EmployeeServiceRecord(user_id=10, employee_category="faculty")
    policy = HRPolicyVersion(policy_name="hr", version=2, effective_from=date.today())
    request = HRRequest(owner_user_id=10, request_type="leave", pk=4)
    notification = NotificationRecord(user_id=10, topic="request.submitted")
    decision = RequestDecision(request_id=4, event="submit")
    audit = AuditEvent(action="test", resource_type="request", resource_id=4)
    assert str(employee) == "service record for user 10"
    assert str(policy) == "hr v2"
    assert str(request) == "leave request #4 (draft)"
    assert str(notification) == "request.submitted for user 10"
    assert str(decision) == "request #4: submit"
    assert str(audit) == "test on request #4"
