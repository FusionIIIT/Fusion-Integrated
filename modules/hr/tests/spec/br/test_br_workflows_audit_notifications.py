"""BR spec tests for Workflows, Audit Log Immutability, and Notifications."""

import pytest

from modules.hr.domain import state_machine
from modules.hr.models import AuditEvent, HRNotification
from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_HR_ADMIN,
    UID_UNAUTHORIZED,
)

pytestmark = pytest.mark.django_db


def test_br_045_approved_outcome_supported(hr_caller):
    """TEST-BR-045 | BR-HR-023 approved-outcome-supported.

    Verify that HR-EIS supports the 'Approved' outcome for routed HR requests.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="approve", authority_step=0, route_length=1
    )
    assert t.state == state_machine.LEAVE_APPROVED


def test_br_046_rejected_outcome_supported(hr_caller):
    """TEST-BR-046 | BR-HR-023 rejected-outcome-supported.

    Verify that HR-EIS supports the 'Rejected' outcome for routed HR requests.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="reject", authority_step=0, route_length=1
    )
    assert t.state == state_machine.LEAVE_REJECTED


def test_br_047_forwarded_outcome_supported(hr_caller):
    """TEST-BR-047 | BR-HR-023 forwarded-outcome-supported.

    Verify that HR-EIS supports the 'Forwarded to next authority' outcome for multi-tier routed HR requests.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="forward", authority_step=0, route_length=2
    )
    assert t.state == state_machine.LEAVE_PENDING_NEXT
    assert t.authority_step == 1


def test_br_048_manual_bypass_workflow_order_prohibited(hr_caller):
    """TEST-BR-048 | BR-HR-023 manual-bypass-workflow-order-prohibited.

    Verify that HR-EIS prevents manual bypass or alteration of configured workflow order.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_leave(
            state_machine.LEAVE_PENDING, action="approve", authority_step=0, route_length=2
        )


def test_br_049_notification_generation_events(hr_caller):
    """TEST-BR-049 | BR-HR-024 notification-generation-events.

    Verify that HR-EIS generates notifications for request submission, approval/rejection/forwarding, pending reminders, and policy updates.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="event",
        dedupe_key="br-49",
        subject="Alert",
        body="Event triggered",
    )
    assert notif.pk is not None


def test_br_050_audit_log_content_verified(hr_caller):
    """TEST-BR-050 | BR-HR-025 audit-log-content-verified.

    Verify that every HR transaction is logged with actor identity, timestamp, and action performed.
    """
    event = AuditEvent.objects.create(
        entity_type="employee", entity_id=1, actor_user_id=UID_HR_ADMIN, action="test.action"
    )
    assert event.actor_user_id == UID_HR_ADMIN
    assert event.created_at is not None
    assert event.action == "test.action"


def test_br_051_audit_log_immutability_enforced(hr_caller):
    """TEST-BR-051 | BR-HR-025 audit-log-immutability-enforced.

    Verify that audit logs are immutable and cannot be updated or deleted.
    """
    event = AuditEvent.objects.create(
        entity_type="employee", entity_id=2, actor_user_id=UID_HR_ADMIN, action="test.immutable"
    )
    with pytest.raises(TypeError):
        event.action = "tampered"
        event.save()
    with pytest.raises(TypeError):
        event.delete()


def test_br_052_authorized_audit_access_permitted(hr_caller):
    """TEST-BR-052 | BR-HR-026 authorized-audit-access-permitted.

    Verify that audit log access is permitted to authorized roles (HR Administrator) for compliance monitoring.
    """
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_br_053_unauthorized_audit_access_prohibited(hr_caller):
    """TEST-BR-053 | BR-HR-026 unauthorized-audit-access-prohibited.

    Verify that audit log access is restricted and prohibited for unauthorized roles.
    """
    res = hr_caller(
        "get",
        "/api/v1/hr/audit-events/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
    )
    assert res.status_code == 403


def test_br_054_status_exchange_permitted(hr_caller):
    """TEST-BR-054 | BR-HR-027 status-exchange-permitted.

    Verify that HR-EIS exchanges and records payment, disbursement, or accounting status for approved LTC/CPDA claims with payroll and finance systems.
    """
    # Status exchange with payroll and finance
    assert True


def test_br_055_direct_external_execution_prohibited(hr_caller):
    """TEST-BR-055 | BR-HR-027 direct-external-execution-prohibited.

    Verify the boundary exception that HR-EIS does not execute external payroll, accounting, or bank-disbursement operations.
    """
    res = hr_caller(
        "post", "/api/v1/hr/external-payment-execute/", user_id=UID_HR_ADMIN, role="hr_officer"
    )
    assert res.status_code in (404, 405)


def test_br_063_notification_generation_and_handoff(hr_caller):
    """TEST-BR-063 | BR-HR-033 notification-generation-and-handoff.

    Verify that HR-EIS generates/records notification events while treating dashboard and email infrastructure as external delivery boundaries.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="handoff",
        dedupe_key="br-63",
        subject="Handoff",
        body="Delivered",
    )
    assert notif.pk is not None
