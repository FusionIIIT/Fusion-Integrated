from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.employee_leave import services
from modules.employee_leave.models import (
    LeaveBalance,
    LeaveHoliday,
    LeavePolicy,
    LeaveRequest,
    LeaveTaskNotice,
    LeaveYearEndRun,
)
from modules.employee_leave.services import (
    act,
    process_sla,
    process_year_end,
    request_extension,
    submit,
    task_notices_for,
    visible_requests,
)

pytestmark = pytest.mark.django_db


def _policy():
    return LeavePolicy.objects.create(leave_type="EL", leave_year=2026, annual_entitlement="30")


def _directory(monkeypatch, **departments):
    people = {
        int(user_id): SimpleNamespace(
            user_id=int(user_id), kind="faculty", is_active=True, department=department
        )
        for user_id, department in departments.items()
    }
    monkeypatch.setattr(
        services.directory,
        "get_users",
        lambda ids: {user_id: people[user_id] for user_id in ids if user_id in people},
    )
    return people


def test_rejecting_cancellation_does_not_refund_the_approved_leave(monkeypatch):
    _directory(monkeypatch, **{"1001": "Mechanical", "2001": "Mechanical"})
    policy = _policy()
    parent = LeaveRequest.objects.create(
        employee_id=1001,
        department="Mechanical",
        policy=policy,
        request_kind="new",
        leave_type="EL",
        start_date="2026-11-10",
        end_date="2026-11-13",
        charged_days="4",
        reason="Approved leave",
        status="approved",
        final_decision="approved",
    )
    cancellation = LeaveRequest.objects.create(
        employee_id=1001,
        department="Mechanical",
        policy=policy,
        parent=parent,
        request_kind="cancellation",
        leave_type="EL",
        start_date=parent.start_date,
        end_date=parent.end_date,
        charged_days=parent.charged_days,
        reason="Employee requested cancellation",
        status="cancellation_unit_head_pending",
        assigned_role="unit_head",
    )
    balance = LeaveBalance.objects.create(
        user_id=1001, policy=policy, opening_balance="20", used="4"
    )
    actor = make_principal(
        user_id=2001,
        modules=("employee_leave",),
        permissions=("employee_leave.request.review_unit",),
        roles=("unit_head",),
        active_role="unit_head",
    )

    result = act(
        request_id=cancellation.pk,
        actor=actor,
        action="reject_cancellation",
        comment="Leave remains approved",
    )

    balance.refresh_from_db()
    parent.refresh_from_db()
    assert result.status == "rejected"
    assert result.final_decision == "rejected"
    assert balance.used == 4
    assert parent.status == "approved"
    assert parent.final_decision == "approved"


def test_unit_head_cannot_approve_their_own_leave_request(monkeypatch):
    _directory(monkeypatch, **{"1001": "Mechanical"})
    policy = _policy()
    request = LeaveRequest.objects.create(
        employee_id=1001,
        department="Mechanical",
        policy=policy,
        request_kind="new",
        leave_type="EL",
        start_date="2026-11-10",
        end_date="2026-11-13",
        charged_days="4",
        reason="Own leave",
        status="unit_head_pending",
        assigned_role="unit_head",
    )
    LeaveBalance.objects.create(user_id=1001, policy=policy, opening_balance="20")
    actor = make_principal(
        user_id=1001,
        kind="faculty",
        modules=("employee_leave",),
        permissions=("employee_leave.request.create", "employee_leave.request.review_unit"),
        roles=("unit_head",),
        active_role="unit_head",
    )

    with pytest.raises(PermissionDeniedError):
        act(request_id=request.pk, actor=actor, action="approve")

    request.refresh_from_db()
    assert request.status == "unit_head_pending"


def test_unit_head_queue_is_limited_to_their_department(monkeypatch):
    _directory(monkeypatch, **{"2001": "Mechanical"})
    policy = _policy()
    same_department = LeaveRequest.objects.create(
        employee_id=1002,
        department="Mechanical",
        policy=policy,
        leave_type="EL",
        start_date="2026-11-10",
        end_date="2026-11-11",
        charged_days="2",
        reason="Same department",
        status="unit_head_pending",
        assigned_role="unit_head",
    )
    other_department = LeaveRequest.objects.create(
        employee_id=1003,
        department="Electrical",
        policy=policy,
        leave_type="EL",
        start_date="2026-11-10",
        end_date="2026-11-11",
        charged_days="2",
        reason="Different department",
        status="unit_head_pending",
        assigned_role="unit_head",
    )
    actor = make_principal(
        user_id=2001,
        kind="faculty",
        modules=("employee_leave",),
        permissions=("employee_leave.request.review_unit",),
        roles=("unit_head",),
        active_role="unit_head",
    )

    assert list(visible_requests(actor).values_list("id", flat=True)) == [same_department.id]
    with pytest.raises(NotFoundError):
        act(request_id=other_department.pk, actor=actor, action="approve")


def test_year_end_processing_blocks_unresolved_requests():
    policy = LeavePolicy.objects.create(leave_type="EL", leave_year=2026)
    LeavePolicy.objects.create(leave_type="EL", leave_year=2027)
    LeaveRequest.objects.create(
        employee_id=1001,
        policy=policy,
        leave_type="EL",
        start_date="2026-12-20",
        end_date="2026-12-22",
        charged_days="3",
        reason="Still awaiting decision",
        status="unit_head_pending",
    )
    actor = make_principal(
        user_id=9001,
        modules=("employee_leave",),
        permissions=("employee_leave.configuration.manage",),
        roles=("leave_administrator",),
        active_role="leave_administrator",
    )

    with pytest.raises(ConflictError) as error:
        process_year_end(actor=actor, from_year=2026)

    assert error.value.code == "pending_leave_workflows"
    assert not LeaveYearEndRun.objects.exists()


def test_year_end_conversion_never_reports_negative_lapsed_days(monkeypatch):
    source = LeavePolicy.objects.create(
        leave_type="VL",
        leave_year=2026,
        year_end_treatment="convert_to_el",
        carry_forward_limit="10",
        conversion_ratio="2",
    )
    target = LeavePolicy.objects.create(leave_type="EL", leave_year=2027)
    balance = LeaveBalance.objects.create(
        user_id=1001, policy=source, opening_balance="3", used="1"
    )
    monkeypatch.setattr(services.directory, "get_employees", list)
    actor = make_principal(
        user_id=9001,
        modules=("employee_leave",),
        permissions=("employee_leave.configuration.manage",),
        roles=("leave_administrator",),
        active_role="leave_administrator",
    )

    run = process_year_end(actor=actor, from_year=2026)

    target_balance = LeaveBalance.objects.get(user_id=1001, policy=target)
    balance.refresh_from_db()
    assert target_balance.credited == 4
    assert run.converted_to_el == 4
    assert run.lapsed == 0
    assert balance.available == 0


def test_restricted_holiday_request_cannot_span_multiple_days(monkeypatch):
    _directory(monkeypatch, **{"1001": "Mechanical"})
    policy = LeavePolicy.objects.create(leave_type="RH", leave_year=2026)
    LeaveBalance.objects.create(user_id=1001, policy=policy, opening_balance="5")
    LeaveHoliday.objects.create(
        leave_year=2026, day="2026-11-10", name="RH", restricted=True, published=True
    )
    actor = make_principal(
        user_id=1001,
        kind="faculty",
        modules=("employee_leave",),
        permissions=("employee_leave.request.create",),
        roles=("employee",),
        active_role="employee",
    )

    with pytest.raises(ConflictError) as error:
        submit(
            actor=actor,
            leave_type="RH",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 11),
            reason="Trip",
        )

    assert error.value.code == "restricted_holiday_single_day"


def test_extension_obeys_policy_continuous_day_limit(monkeypatch):
    monkeypatch.setattr(services.timezone, "localdate", lambda: date(2026, 10, 11))
    _directory(monkeypatch, **{"1001": "Mechanical"})
    policy = LeavePolicy.objects.create(leave_type="EL", leave_year=2026, max_continuous_days=2)
    parent = LeaveRequest.objects.create(
        employee_id=1001,
        department="Mechanical",
        policy=policy,
        request_kind="new",
        leave_type="EL",
        start_date="2026-10-10",
        end_date="2026-10-12",
        charged_days="3",
        reason="Approved leave",
        status="approved",
    )
    LeaveBalance.objects.create(user_id=1001, policy=policy, opening_balance="10")
    actor = make_principal(
        user_id=1001,
        kind="faculty",
        modules=("employee_leave",),
        permissions=("employee_leave.request.create",),
        roles=("employee",),
        active_role="employee",
    )

    with pytest.raises(ConflictError) as error:
        request_extension(
            actor=actor,
            request_id=parent.pk,
            start_date=date(2026, 10, 13),
            end_date=date(2026, 10, 15),
            reason="Recovery",
        )

    assert error.value.code == "continuous_limit_exceeded"


def test_resumption_rejects_categories_outside_elm_resumption_scope():
    policy = _policy()
    request = LeaveRequest.objects.create(
        employee_id=1001,
        policy=policy,
        request_kind="new",
        leave_type="CL",
        start_date="2026-10-10",
        end_date="2026-10-10",
        charged_days="1",
        reason="Casual leave",
        status="approved",
    )
    actor = make_principal(
        user_id=1001,
        kind="faculty",
        modules=("employee_leave",),
        permissions=("employee_leave.request.create",),
        roles=("employee",),
        active_role="employee",
    )

    with pytest.raises(ConflictError) as error:
        act(
            request_id=request.pk,
            actor=actor,
            action="request_resumption",
            actual_resume_date=date(2026, 10, 12),
        )

    assert error.value.code == "resumption_not_applicable"


def test_sla_scanner_reminds_and_escalates_once_to_the_configured_role():
    policy = LeavePolicy.objects.create(
        leave_type="EL",
        leave_year=2026,
        unit_head_sla_hours=1,
        final_sanction_sla_hours=2,
        escalation_role="sanctioning_authority",
    )
    old_assignment = timezone.now() - timedelta(hours=3)
    request = LeaveRequest.objects.create(
        employee_id=1001,
        department="Mechanical",
        policy=policy,
        leave_type="EL",
        start_date="2026-11-10",
        end_date="2026-11-11",
        charged_days="2",
        reason="Overdue review",
        status="unit_head_pending",
        assigned_role="unit_head",
        assigned_at=old_assignment,
    )

    first = process_sla()
    second = process_sla()

    request.refresh_from_db()
    assert first == {"examined": 1, "reminders": 1, "escalations": 1}
    assert second == {"examined": 1, "reminders": 0, "escalations": 0}
    assert request.assigned_role == "sanctioning_authority"
    assert request.sla_reminded_at is not None
    assert request.sla_escalated_at is not None
    assert list(
        LeaveTaskNotice.objects.filter(request=request).values_list("event", flat=True)
    ) == ["escalated", "reminder"]
    authority = make_principal(
        user_id=9002,
        modules=("employee_leave",),
        permissions=("employee_leave.request.sanction",),
        roles=("sanctioning_authority",),
        active_role="sanctioning_authority",
    )
    assert [notice.event for notice in task_notices_for(authority)] == ["escalated"]
    result = act(
        request_id=request.pk,
        actor=authority,
        action="recommend",
        comment="Forwarding after SLA escalation",
    )
    assert result.status == "final_pending"
