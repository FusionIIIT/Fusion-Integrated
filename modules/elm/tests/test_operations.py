"""Focused operational tests for year-end accounting and pending-task SLAs."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from modules.elm.models import (
    ELMNotification,
    LeaveAccount,
    LeaveCategory,
    LeaveEvent,
    LeaveRequest,
    LeaveReservation,
    LeaveTransaction,
    WorkflowTask,
    YearEndRun,
)

pytestmark = pytest.mark.django_db


def category(code, entitlement, carry=False, rule="working_days"):
    return LeaveCategory.objects.create(
        code=code,
        name=code,
        annual_entitlement=Decimal(entitlement),
        employee_scope="all",
        carry_forward=carry,
        counting_rule=rule,
    )


def test_year_end_lapses_carries_and_converts_vacation_leave():
    cl = category("CL", "8")
    el = category("EL", "30", True, "continuous")
    col = category("COL", "20", True, "continuous")
    vl = category("VL", "60", False, "continuous")
    user_id, year = 901, timezone.localdate().year - 1
    accounts = {
        code: LeaveAccount.objects.create(
            user_id=user_id,
            category=cat,
            year=year,
            annual_entitlement=Decimal(cat.annual_entitlement),
        )
        for code, cat in {"CL": cl, "EL": el, "COL": col, "VL": vl}.items()
    }
    LeaveTransaction.objects.create(
        account=accounts["EL"],
        kind="charge",
        amount=Decimal("-1"),
        reference="used",
        note="Used before close.",
    )
    LeaveTransaction.objects.create(
        account=accounts["VL"],
        kind="charge",
        amount=Decimal("-59.50"),
        reference="used",
        note="Used before close.",
    )

    call_command("run_elm_year_end", year)

    assert YearEndRun.objects.get(year=year).status == "completed"
    assert accounts["CL"].transactions.filter(kind="lapse", amount=Decimal("-8")).exists()
    el_next = LeaveAccount.objects.get(user_id=user_id, category=el, year=year + 1)
    assert el_next.transactions.get(kind="credit").amount == Decimal("29.00")
    col_next = LeaveAccount.objects.get(user_id=user_id, category=col, year=year + 1)
    assert col_next.transactions.get(kind="credit").amount == Decimal("20.00")
    vl_conversion = accounts["VL"].transactions.get(kind="conversion")
    assert vl_conversion.amount == Decimal("-0.50")
    assert el_next.transactions.get(kind="conversion").amount == Decimal("0.25")


def test_year_end_is_not_applied_twice():
    year = timezone.localdate().year - 1
    category("CL", "8")
    LeaveAccount.objects.create(
        user_id=902,
        category=LeaveCategory.objects.get(code="CL"),
        year=year,
        annual_entitlement=Decimal("8"),
    )
    call_command("run_elm_year_end", year)
    with pytest.raises(CommandError, match="already complete"):
        call_command("run_elm_year_end", year)


def test_year_end_rejects_current_and_future_years():
    current_year = timezone.localdate().year
    for year in (current_year, current_year + 1):
        with pytest.raises(CommandError, match="completed year"):
            call_command("run_elm_year_end", year)


def test_year_end_preflights_all_accounts_and_can_retry_after_correction():
    year = timezone.localdate().year - 1
    el = category("EL", "30", True, "continuous")
    cl = category("CL", "8")
    carry_account = LeaveAccount.objects.create(
        user_id=904, category=el, year=year, annual_entitlement=Decimal("30")
    )
    cl_account = LeaveAccount.objects.create(
        user_id=905, category=cl, year=year, annual_entitlement=Decimal("8")
    )
    pending = LeaveRequest.objects.create(
        employee_user_id=905,
        category=cl,
        request_type="new",
        status="awaiting_unit_head",
        starts_on=timezone.localdate(),
        ends_on=timezone.localdate(),
        chargeable_days=Decimal("1"),
        reason="Pending leave",
    )
    reservation = LeaveReservation.objects.create(
        request=pending, account=cl_account, amount=Decimal("1")
    )
    with pytest.raises(CommandError, match="exception"):
        call_command("run_elm_year_end", year)
    run = YearEndRun.objects.get(year=year)
    assert run.status == "failed"
    assert run.exceptions[0]["reason"] == "active_reservations"
    assert not LeaveAccount.objects.filter(user_id=904, category=el, year=year + 1).exists()
    assert not carry_account.transactions.filter(reference=f"year-end:{year}").exists()

    reservation.is_active = False
    reservation.save(update_fields=["is_active"])
    call_command("run_elm_year_end", year)
    run.refresh_from_db()
    assert run.status == "completed"
    carried = LeaveAccount.objects.get(user_id=904, category=el, year=year + 1)
    assert carried.transactions.get(reference=f"year-end:{year}").amount == Decimal("30")


def test_year_end_missing_conversion_category_fails_without_partial_posts_and_retries():
    year = timezone.localdate().year - 1
    vl = category("VL", "60", False, "continuous")
    old_account = LeaveAccount.objects.create(
        user_id=906, category=vl, year=year, annual_entitlement=Decimal("60")
    )
    with pytest.raises(CommandError, match="exception"):
        call_command("run_elm_year_end", year)
    run = YearEndRun.objects.get(year=year)
    assert run.status == "failed"
    assert run.exceptions[0]["reason"] == "EL_category_missing"
    assert not LeaveAccount.objects.filter(user_id=906, category=vl, year=year + 1).exists()
    assert not old_account.transactions.filter(reference=f"year-end:{year}").exists()

    earned = category("EL", "30", True, "continuous")
    call_command("run_elm_year_end", year)
    run.refresh_from_db()
    assert run.status == "completed"
    target = LeaveAccount.objects.get(user_id=906, category=earned, year=year + 1)
    assert target.transactions.get(kind="conversion").amount == Decimal("30")


def test_sla_reminder_and_escalation_are_logged_once_while_pending():
    cl = category("CL", "8")
    request = LeaveRequest.objects.create(
        employee_user_id=903,
        category=cl,
        request_type="new",
        status="awaiting_unit_head",
        starts_on=timezone.localdate(),
        ends_on=timezone.localdate(),
        chargeable_days=Decimal("1"),
        reason="Test",
    )
    task = WorkflowTask.objects.create(
        request=request,
        task_type="unit_head",
        assigned_to_user_id=904,
        reminder_after_hours=1,
        escalation_after_hours=2,
        escalation_user_id=905,
    )
    WorkflowTask.objects.filter(pk=task.pk).update(assigned_at=timezone.now() - timedelta(hours=3))

    call_command("run_elm_sla")
    call_command("run_elm_sla")

    task.refresh_from_db()
    assert task.reminded_at is not None
    assert task.escalated_at is not None
    assert ELMNotification.objects.filter(request=request, kind="sla_reminder").count() == 1
    assert ELMNotification.objects.filter(request=request, kind="sla_escalation").count() == 1
    assert LeaveEvent.objects.filter(request=request, event_type="sla_reminder").count() == 1
    assert LeaveEvent.objects.filter(request=request, event_type="sla_escalated").count() == 1
