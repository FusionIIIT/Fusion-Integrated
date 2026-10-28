from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import (
    ApprovalRoute,
    ELMNotificationOutbox,
    EmployeeProfile,
    LeaveAccount,
    LeavePolicy,
    LeaveRequest,
    LeaveTransaction,
    OrgUnit,
    RequestEvent,
)
from modules.elm.services import leave

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee():
    unit = OrgUnit.objects.create(
        code="engineering", name="Engineering", unit_head_user_id=200)
    applicant = EmployeeProfile.objects.create(
        user_id=100, employee_kind="staff", unit=unit)
    EmployeeProfile.objects.create(
        user_id=200, employee_kind="staff", unit=unit)
    EmployeeProfile.objects.create(
        user_id=300, employee_kind="staff", unit=unit)
    EmployeeProfile.objects.create(
        user_id=400, employee_kind="staff", unit=unit)
    for year in range(date.today().year - 2, date.today().year + 4):
        LeavePolicy.objects.create(year=year)
    return applicant


def _submit_cl(*, substitute=None, starts_on=None, ends_on=None):
    starts_on = starts_on or date.today() + timedelta(days=14)
    ends_on = ends_on or starts_on
    return leave.submit_leave(
        applicant_user_id=100, category="CL",
        starts_on=starts_on, ends_on=ends_on,
        purpose="Personal leave", substitute_user_id=substitute)


def _approve(request):
    task = request.tasks.get(status="pending")
    return leave.decide_task(
        request_id=request.pk, task_id=task.pk, actor_id=200,
        action="approve")


def test_approval_debits_balance_and_records_an_idempotent_transaction(employee):
    request = _submit_cl()
    _approve(request)

    account = LeaveAccount.objects.get(
        user_id=100, category="CL", year=request.starts_on.year)
    assert request.__class__.objects.get(pk=request.pk).status == "approved"
    assert account.balance == Decimal("7")
    debit = LeaveTransaction.objects.get(
        request=request, transaction_type="leave_debit")
    assert debit.amount == Decimal("-1")
    assert debit.idempotency_key == f"request:{request.pk}:approval:{request.starts_on.year}"


def test_actionable_assignment_is_queued_once_for_email_delivery(employee):
    request = _submit_cl()
    task = request.tasks.get(status="pending")
    notification = ELMNotificationOutbox.objects.get(
        dedupe_key=f"task:{task.pk}:assigned")
    assert notification.topic == "task_assigned"
    assert notification.recipient_user_id == 200
    assert notification.status == "pending"


def test_notification_delivery_uses_directory_email_and_records_success(
    employee, monkeypatch,
):
    from modules.directory.contracts import UserDTO
    from modules.elm.services import notifications

    request = _submit_cl()
    task = request.tasks.get(status="pending")
    sent = []
    monkeypatch.setattr(
        "modules.directory.contracts.get_users",
        lambda ids: {
            user_id: UserDTO(
                user_id=user_id, username="reviewer", display_name="Reviewer",
                kind="staff", email="reviewer@example.test")
            for user_id in ids
        })
    monkeypatch.setattr(notifications, "send_mail", lambda **kwargs: sent.append(kwargs))

    result = notifications.deliver_pending()

    notification = ELMNotificationOutbox.objects.get(
        dedupe_key=f"task:{task.pk}:assigned")
    assert result["sent"] == 1
    assert notification.status == "sent"
    assert sent[0]["recipient_list"] == ["reviewer@example.test"]


def test_substitute_decline_allows_only_one_replacement(employee):
    applicant = EmployeeProfile.objects.get(user_id=100)
    applicant.requires_substitute = True
    applicant.save(update_fields=["requires_substitute", "updated_at"])
    request = _submit_cl(substitute=300)

    leave.respond_to_substitute(request_id=request.pk, actor_id=300, accept=False)
    request.refresh_from_db()
    assert request.status == "applicant_action_required"
    event = request.events.get(event="substitute_declined")
    assert event.to_status == request.status
    assert RequestEvent._meta.get_field("to_status").max_length >= len(request.status)
    with pytest.raises(NotFoundError):
        leave.respond_to_substitute(request_id=request.pk, actor_id=300, accept=True)
    leave.replace_substitute(
        request_id=request.pk, applicant_id=100, substitute_user_id=400)
    request.refresh_from_db()
    assert request.status == "substitute_pending"
    leave.respond_to_substitute(request_id=request.pk, actor_id=400, accept=False)

    with pytest.raises(ConflictError) as exc_info:
        leave.replace_substitute(
            request_id=request.pk, applicant_id=100, substitute_user_id=300)
    assert exc_info.value.code == "substitute_replacement_limit"


def test_cross_year_leave_uses_and_debits_each_years_balance(employee):
    request = _submit_cl(
        starts_on=date(2027, 12, 30),
        ends_on=date(2028, 1, 3),
    )
    assert request.requested_days == Decimal("3")
    _approve(request)

    accounts = {
        account.year: account.balance
        for account in LeaveAccount.objects.filter(
            user_id=100, category="CL", year__in=(2027, 2028))
    }
    assert accounts == {2027: Decimal("6"), 2028: Decimal("7")}
    debits = list(
        LeaveTransaction.objects.filter(
            request=request, transaction_type="leave_debit",
        ).order_by("account__year").values_list("amount", flat=True)
    )
    assert debits == [Decimal("-2"), Decimal("-1")]


def test_cancellation_restores_all_debits(employee):
    request = _submit_cl(
        starts_on=date(2027, 12, 30),
        ends_on=date(2028, 1, 3),
    )
    _approve(request)
    cancellation = leave.request_cancellation(
        request_id=request.pk, applicant_id=100, purpose="Plans changed")
    _approve(cancellation)

    accounts = {
        account.year: account.balance
        for account in LeaveAccount.objects.filter(
            user_id=100, category="CL", year__in=(2027, 2028))
    }
    assert accounts == {2027: Decimal("8"), 2028: Decimal("8")}
    assert LeaveRequest.objects.get(pk=request.pk).status == "cancelled"


def test_request_with_invalid_half_day_is_rejected(employee):
    starts_on = date.today() + timedelta(days=14)
    with pytest.raises(ConflictError) as exc_info:
        leave.submit_leave(
            applicant_user_id=100, category="CL",
            starts_on=starts_on, ends_on=starts_on,
            purpose="Personal leave", half_day_part="morning",
        )
    assert exc_info.value.code == "invalid_half_day"


def test_year_end_is_not_repeatable(employee):
    from modules.elm.services.year_end import process_year_end

    process_year_end(year=date.today().year - 1, actor_user_id=200)
    with pytest.raises(ConflictError) as exc_info:
        process_year_end(year=date.today().year - 1, actor_user_id=200)
    assert exc_info.value.code == "year_end_already_run"


def test_late_resumption_adjustment_cannot_create_negative_balance(employee):
    unit = employee.unit
    ApprovalRoute.objects.create(
        category="EL", unit=unit,
        steps=[{"user_id": 200, "role": "Registrar"}])
    account = LeaveAccount.objects.create(
        user_id=100, category="EL", year=date.today().year,
        entitlement=Decimal("30"), balance=Decimal("0"), used=Decimal("2"))
    original = LeaveRequest.objects.create(
        applicant_user_id=100, category="EL", status="approved",
        starts_on=date.today() - timedelta(days=8),
        ends_on=date.today() - timedelta(days=2),
        requested_days=Decimal("2"), purpose="Medical leave")
    resumption = LeaveRequest.objects.create(
        applicant_user_id=100, category="EL", request_type="resumption",
        parent=original, status="pending", starts_on=original.starts_on,
        ends_on=original.ends_on, actual_resume_date=date.today(),
        requested_days=Decimal("0"), purpose="Return to duty")
    with pytest.raises(ConflictError) as exc_info:
        leave._apply_resumption(resumption, actor_id=200)
    assert exc_info.value.code == "insufficient_balance"
    account.refresh_from_db()
    assert account.balance == Decimal("0")


def test_unit_specific_approval_route_precedes_global_fallback(employee):
    global_route = ApprovalRoute.objects.create(
        category="EL", steps=[{"user_id": 201, "role": "Global Authority"}])
    unit_route = ApprovalRoute.objects.create(
        category="EL", unit=employee.unit,
        steps=[{"user_id": 202, "role": "Unit Authority"}])
    request = LeaveRequest(
        applicant_user_id=employee.user_id, category="EL",
        starts_on=date.today(), ends_on=date.today(), purpose="Route test")

    route_steps = leave._route_steps(request)

    assert route_steps[-1] == ("Unit Authority", 202, True)
    assert global_route.pk != unit_route.pk


def test_offline_leave_synchronizes_balance_without_creating_approval_tasks(employee):
    today = date.today()
    workdays = [
        today - timedelta(days=offset)
        for offset in range(1, 15)
        if (today - timedelta(days=offset)).weekday() < 5
    ][:2]
    request = leave.record_offline_leave(
        applicant_user_id=100, actor_id=900, category="CL",
        starts_on=min(workdays), ends_on=max(workdays),
        purpose="Previously sanctioned leave",
        offline_reference="ORD-2026-001",
        offline_reason="ELM unavailable during approved institute outage",
        offline_sanctioned_on=today - timedelta(days=10),
    )

    account = LeaveAccount.objects.get(
        user_id=100, category="CL", year=today.year)
    assert request.status == "approved"
    assert request.offline_reference == "ORD-2026-001"
    assert not request.tasks.exists()
    assert account.balance == Decimal("6")
    assert account.used == Decimal("2")
    assert request.transactions.get().transaction_type == "offline_entry"
    assert request.events.get().event == "offline_leave_synchronized"


def test_offline_leave_rejects_duplicate_reference_and_insufficient_balance(employee):
    today = date.today()
    workdays = [
        today - timedelta(days=offset)
        for offset in range(1, 15)
        if (today - timedelta(days=offset)).weekday() < 5
    ][:2]
    params = {
        "applicant_user_id": 100, "actor_id": 900, "category": "CL",
        "starts_on": min(workdays), "ends_on": max(workdays),
        "purpose": "Offline leave",
        "offline_reference": "ORD-2026-002", "offline_reason": "ELM outage",
        "offline_sanctioned_on": today - timedelta(days=10),
    }
    leave.record_offline_leave(**params)
    with pytest.raises(ConflictError) as duplicate:
        leave.record_offline_leave(**params)
    assert duplicate.value.code == "duplicate_offline_reference"

    account = LeaveAccount.objects.get(
        user_id=100, category="CL", year=today.year)
    account.balance = Decimal("0")
    account.save(update_fields=["balance", "updated_at"])
    separate_workdays = [
        today + timedelta(days=offset)
        for offset in range(1, 15)
        if (today + timedelta(days=offset)).weekday() < 5
    ][:2]
    with pytest.raises(ConflictError) as insufficient:
        leave.record_offline_leave(
            **{
                **params,
                "starts_on": min(separate_workdays),
                "ends_on": max(separate_workdays),
                "offline_reference": "ORD-2026-003",
            })
    assert insufficient.value.code == "insufficient_balance"


def test_sla_processing_logs_pending_only_and_is_idempotent(employee):
    unit = employee.unit
    ApprovalRoute.objects.create(
        category="EL", unit=unit,
        steps=[{"user_id": 300, "role": "Registrar"}])
    request = leave.submit_leave(
        applicant_user_id=100, category="EL",
        starts_on=date.today() + timedelta(days=14),
        ends_on=date.today() + timedelta(days=14),
        purpose="SLA test")
    task = request.tasks.get(status="pending")
    policy = LeavePolicy.objects.get(year=request.starts_on.year)
    policy.reminder_after_hours = 1
    policy.escalate_after_hours = 2
    policy.escalation_user_id = 400
    policy.save(update_fields=[
        "reminder_after_hours", "escalate_after_hours",
        "escalation_user_id", "updated_at"])
    now = task.assigned_at + timedelta(hours=3)

    from modules.elm.services.sla import process_sla_thresholds

    report = process_sla_thresholds(now=now)
    task.refresh_from_db()
    assert report == {"reminded": 1, "escalated": 1, "skipped": 0}
    assert task.reminder_sent_at == now
    assert task.escalation_sent_at == now
    assert request.events.filter(
        event__in=("sla_reminder", "sla_escalation")).count() == 2
    escalation = ELMNotificationOutbox.objects.get(
        dedupe_key=f"task:{task.pk}:escalation")
    assert escalation.recipient_user_id == 400

    assert process_sla_thresholds(now=now) == {
        "reminded": 0, "escalated": 0, "skipped": 0}
    assert ELMNotificationOutbox.objects.count() == 3


def test_sla_does_not_notify_tasks_that_are_no_longer_pending(employee):
    request = _submit_cl()
    task = request.tasks.get(status="pending")
    task.status = "approved"
    task.save(update_fields=["status", "updated_at"])

    from modules.elm.services.sla import process_sla_thresholds

    now = task.assigned_at + timedelta(days=10)
    assert process_sla_thresholds(now=now) == {
        "reminded": 0, "escalated": 0, "skipped": 0}
    assert not ELMNotificationOutbox.objects.filter(
        recipient_user_id=task.assigned_user_id,
        topic__in=("task_reminder", "task_escalation")).exists()


def test_waiting_task_sla_clock_starts_when_the_task_becomes_actionable(employee):
    ApprovalRoute.objects.create(
        category="EL", unit=employee.unit,
        steps=[{"user_id": 300, "role": "Registrar"}])
    request = leave.submit_leave(
        applicant_user_id=100, category="EL",
        starts_on=date.today() + timedelta(days=14),
        ends_on=date.today() + timedelta(days=14),
        purpose="Task activation test")
    first = request.tasks.get(status="pending")
    waiting = request.tasks.get(status="waiting")
    old_assigned_at = timezone.now() - timedelta(days=10)
    waiting.assigned_at = old_assigned_at
    waiting.save(update_fields=["assigned_at", "updated_at"])

    leave.decide_task(
        request_id=request.pk, task_id=first.pk, actor_id=200,
        action="recommend")

    waiting.refresh_from_db()
    assert waiting.status == "pending"
    assert waiting.assigned_at > old_assigned_at
    assert ELMNotificationOutbox.objects.filter(
        dedupe_key=f"task:{waiting.pk}:assigned").exists()


def test_approved_record_maintenance_is_audited_without_changing_sanction(employee):
    from modules.elm.services.records import maintain_leave_record

    request = _submit_cl()
    _approve(request)
    request.refresh_from_db()
    original_status = request.status
    result = maintain_leave_record(
        request_id=request.pk, actor_id=900, reason="Corrected typo",
        changes={"purpose": "Updated personal reason"})

    assert result.status == original_status == "approved"
    assert result.starts_on == request.starts_on
    assert result.purpose == "Updated personal reason"
    assert result.tasks.filter(status="approved").count() == 1
    event = result.events.get(event="record_maintained")
    assert "Corrected typo" in event.note
    assert '"before": "Personal leave"' in event.note


def test_pending_request_cannot_be_changed_by_record_maintenance(employee):
    request = _submit_cl()
    from modules.elm.services.records import maintain_leave_record

    with pytest.raises(ConflictError) as exc_info:
        maintain_leave_record(
            request_id=request.pk, actor_id=900, reason="Attempted edit",
            changes={"purpose": "Changed after submission"})
    assert exc_info.value.code == "record_not_maintainable"
    request.refresh_from_db()
    assert request.purpose == "Personal leave"


def test_early_resumption_restores_chargeable_days(employee):
    today = date.today()
    start = today - timedelta(days=10)
    end = today - timedelta(days=2)
    actual_resume = today - timedelta(days=5)
    account = LeaveAccount.objects.create(
        user_id=100, category="EL", year=today.year,
        entitlement=Decimal("30"), balance=Decimal("22"), used=Decimal("8"))
    original = LeaveRequest.objects.create(
        applicant_user_id=100, category="EL", status="approved",
        starts_on=start, ends_on=end, requested_days=Decimal("8"),
        purpose="Medical leave")
    resumption = LeaveRequest.objects.create(
        applicant_user_id=100, category="EL", request_type="resumption",
        parent=original, status="pending", starts_on=start, ends_on=end,
        actual_resume_date=actual_resume, requested_days=Decimal("0"),
        purpose="Early return")
    adjustment_days = leave._count_days(
        "EL", actual_resume + timedelta(days=1), end, "")

    leave._apply_resumption(resumption, actor_id=200)

    account.refresh_from_db()
    assert account.balance == Decimal("22") + adjustment_days
    assert account.used == Decimal("8") - adjustment_days


def test_normal_resumption_does_not_adjust_the_leave_account(employee):
    today = date.today()
    start = today - timedelta(days=8)
    end = today
    account = LeaveAccount.objects.create(
        user_id=100, category="EL", year=today.year,
        entitlement=Decimal("30"), balance=Decimal("22"), used=Decimal("8"))
    original = LeaveRequest.objects.create(
        applicant_user_id=100, category="EL", status="approved",
        starts_on=start, ends_on=end, requested_days=Decimal("8"),
        purpose="Medical leave")
    resumption = LeaveRequest.objects.create(
        applicant_user_id=100, category="EL", request_type="resumption",
        parent=original, status="pending", starts_on=start, ends_on=end,
        actual_resume_date=today, requested_days=Decimal("0"),
        purpose="Normal return")

    leave._apply_resumption(resumption, actor_id=200)

    account.refresh_from_db()
    assert account.balance == Decimal("22")
    assert account.used == Decimal("8")
    assert not resumption.transactions.exists()
    original.refresh_from_db()
    assert original.status == "approved"


def test_account_scopes_profile_to_active_employee(employee):
    employee.is_active = False
    employee.save(update_fields=["is_active", "updated_at"])
    with pytest.raises(ConflictError) as exc_info:
        leave.account_for(100, "CL")
    assert exc_info.value.code == "employee_profile_missing"
