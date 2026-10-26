from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from modules.elm.domain.policy import LeavePolicyError
from modules.elm.models import (
    LeaveAuthorityRule,
    LeaveBalance,
    LeaveCalendar,
    LeaveCalendarDate,
    LeavePolicy,
    LeaveRequest,
)
from modules.elm.services import leave_request_service as service


@pytest.fixture(autouse=True)
def employee_directory(monkeypatch):
    def fake_get_users(user_ids):
        return {
            int(user_id): SimpleNamespace(
                user_id=int(user_id),
                kind=("faculty" if int(user_id) == 4110 else "staff"),
                department="Engineering",
            )
            for user_id in user_ids
        }

    monkeypatch.setattr(service, "get_users", fake_get_users)


@pytest.fixture
def cl_policy(db):
    policy, _ = LeavePolicy.objects.update_or_create(
        leave_type_code="CL",
        defaults={
            "employee_kinds": ["staff"],
            "annual_entitlement": Decimal("8"),
            "day_counting": "WORKING_DAYS",
            "half_day_allowed": True,
        },
    )
    return policy


@pytest.fixture
def weekday_calendar(db):
    return LeaveCalendar.objects.create(
        kind="HOLIDAY",
        year=2026,
        revision=1,
        label="Test work calendar",
        status="PUBLISHED",
        effective_from=date(2026, 1, 1),
        effective_through=date(2026, 12, 31),
        working_weekdays=[0, 1, 2, 3, 4],
    )


def submit_cl(user_id, substitute_id, **extra):
    return service.LeaveRequestService.submit_request(
        user_id=user_id,
        employee_kind="staff",
        leave_type_code="CL",
        requested_start_date=date(2026, 10, 26),
        requested_end_date=date(2026, 10, 26),
        substitute_user_id=substitute_id,
        **extra,
    )


@pytest.mark.django_db
def test_submission_reserves_configured_balance_and_waits_for_substitute(
    weekday_calendar, cl_policy
):
    request = submit_cl(4107, 5107)
    balance = LeaveBalance.objects.get(
        user_id=4107, leave_type_code="CL", year=2026
    )

    assert request.user_id == 4107
    assert request.status == "PENDING_SUBSTITUTE"
    assert request.substitute_status == "PENDING"
    assert request.total_days == Decimal("1")
    assert balance.annual_credit == Decimal("8")
    assert balance.reserved_days == Decimal("1")
    assert balance.available_days == Decimal("7")
    assert request.balance_events.get().event_type == "RESERVE"
    assert request.history.get().event_type == "SUBMITTED"


@pytest.mark.django_db
def test_half_day_requests_in_different_cl_halves_do_not_overlap(
    weekday_calendar, cl_policy
):
    base = {
        "user_id": 4108,
        "employee_kind": "staff",
        "leave_type_code": "CL",
        "requested_start_date": date(2026, 10, 26),
        "requested_end_date": date(2026, 10, 26),
        "substitute_user_id": 5108,
    }
    first = service.LeaveRequestService.submit_request(
        **base, day_part="FIRST_HALF"
    )
    second = service.LeaveRequestService.submit_request(
        **base, day_part="SECOND_HALF"
    )

    assert first.total_days == second.total_days == Decimal("0.5")
    assert LeaveRequest.objects.filter(user_id=4108).count() == 2

    with pytest.raises(LeavePolicyError, match="overlaps"):
        service.LeaveRequestService.submit_request(
            **base, day_part="FIRST_HALF"
        )


@pytest.mark.django_db
def test_vacation_leave_is_restricted_to_faculty_and_published_vacation_dates(db):
    LeavePolicy.objects.update_or_create(
        leave_type_code="VL",
        defaults={
            "employee_kinds": ["faculty"],
            "annual_entitlement": Decimal("60"),
            "day_counting": "VACATION_DAYS",
        },
    )
    calendar = LeaveCalendar.objects.create(
        kind="VACATION",
        year=2026,
        revision=1,
        label="Test vacation calendar",
        status="PUBLISHED",
        effective_from=date(2026, 1, 1),
        effective_through=date(2026, 12, 31),
    )
    LeaveCalendarDate.objects.create(calendar=calendar, day=date(2026, 6, 1))

    with pytest.raises(LeavePolicyError, match="not eligible"):
        service.LeaveRequestService.submit_request(
            user_id=4109,
            employee_kind="staff",
            leave_type_code="VL",
            requested_start_date=date(2026, 6, 1),
            requested_end_date=date(2026, 6, 1),
            substitute_user_id=5109,
        )

    with pytest.raises(LeavePolicyError, match="outside"):
        service.LeaveRequestService.submit_request(
            user_id=4110,
            employee_kind="faculty",
            leave_type_code="VL",
            requested_start_date=date(2026, 6, 2),
            requested_end_date=date(2026, 6, 2),
            substitute_user_id=5110,
        )


@pytest.mark.django_db
def test_withdrawal_releases_reserved_balance_and_records_history(
    weekday_calendar, cl_policy
):
    request = submit_cl(4111, 5111)
    withdrawn = service.LeaveRequestService.withdraw_request(
        request_id=request.pk,
        user_id=4111,
    )
    balance = LeaveBalance.objects.get(
        user_id=4111, leave_type_code="CL", year=2026
    )

    assert withdrawn.status == "WITHDRAWN"
    assert balance.reserved_days == Decimal("0")
    assert balance.available_days == Decimal("8")
    assert set(
        withdrawn.balance_events.values_list("event_type", flat=True)
    ) == {"RESERVE", "RELEASE"}
    assert list(
        withdrawn.history.values_list("to_status", flat=True)
    ) == ["PENDING_SUBSTITUTE", "WITHDRAWN"]


@pytest.mark.django_db
def test_employee_cannot_withdraw_another_employees_request(
    weekday_calendar, cl_policy
):
    request = submit_cl(4112, 5112)
    with pytest.raises(LeavePolicyError, match="not found"):
        service.LeaveRequestService.withdraw_request(
            request_id=request.pk,
            user_id=9999,
        )


@pytest.mark.django_db
def test_only_nominated_substitute_can_accept_and_acceptance_advances_request(
    weekday_calendar, cl_policy
):
    LeaveAuthorityRule.objects.create(
        department="Engineering",
        leave_type_code="CL",
        step_order=1,
        stage="UNIT_HEAD",
        decision_mode="FINAL",
        approver_user_id=8113,
    )
    request = submit_cl(4113, 5113)
    with pytest.raises(LeavePolicyError, match="not found"):
        service.LeaveRequestService.respond_to_substitute(
            request_id=request.pk,
            actor_user_id=7000,
            action="ACCEPT",
        )

    accepted = service.LeaveRequestService.respond_to_substitute(
        request_id=request.pk,
        actor_user_id=5113,
        action="ACCEPT",
    )
    assert accepted.status == "PENDING_UNIT_HEAD"
    assert accepted.substitute_status == "ACCEPTED"
    assert accepted.approval_tasks.get().assignee_user_id == 8113
    assert accepted.approval_tasks.get().status == "PENDING"
    assert list(accepted.history.values_list("to_status", flat=True)) == [
        "PENDING_SUBSTITUTE",
        "PENDING_UNIT_HEAD",
        "PENDING_UNIT_HEAD",
    ]


@pytest.mark.django_db
def test_decline_allows_one_replacement_then_blocks_another(
    weekday_calendar, cl_policy
):
    request = submit_cl(4114, 5114)
    declined = service.LeaveRequestService.respond_to_substitute(
        request_id=request.pk,
        actor_user_id=5114,
        action="DECLINE",
    )
    assert declined.status == "PENDING_SUBSTITUTE_REPLACEMENT"

    replacement = service.LeaveRequestService.replace_substitute(
        request_id=request.pk,
        user_id=4114,
        new_substitute_user_id=5115,
    )
    assert replacement.status == "PENDING_SUBSTITUTE"
    assert replacement.substitute_user_id == 5115
    assert replacement.substitute_replacement_count == 1

    service.LeaveRequestService.respond_to_substitute(
        request_id=request.pk,
        actor_user_id=5115,
        action="DECLINE",
    )
    with pytest.raises(LeavePolicyError, match="already been used"):
        service.LeaveRequestService.replace_substitute(
            request_id=request.pk,
            user_id=4114,
            new_substitute_user_id=5116,
        )


@pytest.mark.django_db
def test_substitute_must_be_another_employee_without_overlapping_leave(
    weekday_calendar, cl_policy
):
    with pytest.raises(LeavePolicyError, match="cannot nominate themselves"):
        submit_cl(4117, 4117)

    LeaveRequest.objects.create(
        user_id=5118,
        leave_type_code="EL",
        requested_start_date=date(2026, 10, 26),
        requested_end_date=date(2026, 10, 26),
        total_days=Decimal("1"),
        status="APPROVED",
    )
    with pytest.raises(LeavePolicyError, match="has pending or approved leave"):
        submit_cl(4119, 5118)


@pytest.mark.django_db
def test_higher_leave_recommendation_is_not_final_and_final_approval_charges_balance(
    db,
):
    LeavePolicy.objects.update_or_create(
        leave_type_code="EL",
        defaults={
            "employee_kinds": ["staff"],
            "annual_entitlement": Decimal("30"),
            "day_counting": "CALENDAR_DAYS",
            "carries_forward": True,
        },
    )
    rules = (
        ("UNIT_HEAD", "RECOMMEND", 8211),
        ("ESTABLISHMENT", "VERIFY", 8212),
        ("SANCTION", "FINAL", 8213),
    )
    for step, (stage, mode, approver_id) in enumerate(rules, start=1):
        LeaveAuthorityRule.objects.create(
            department="Engineering",
            leave_type_code="EL",
            step_order=step,
            stage=stage,
            decision_mode=mode,
            approver_user_id=approver_id,
        )

    request = service.LeaveRequestService.submit_request(
        user_id=4120,
        employee_kind="staff",
        leave_type_code="EL",
        requested_start_date=date(2026, 10, 26),
        requested_end_date=date(2026, 10, 27),
        substitute_user_id=5120,
    )
    service.LeaveRequestService.respond_to_substitute(
        request_id=request.pk,
        actor_user_id=5120,
        action="ACCEPT",
    )

    with pytest.raises(LeavePolicyError, match="not found"):
        service.LeaveRequestService.decide_request(
            request_id=request.pk,
            actor_user_id=9999,
            action="NOT_RECOMMENDED",
        )

    request = service.LeaveRequestService.decide_request(
        request_id=request.pk,
        actor_user_id=8211,
        action="NOT_RECOMMENDED",
        reason="Coverage concern",
    )
    assert request.status == "PENDING_ESTABLISHMENT"
    assert request.status != "REJECTED"
    assert request.approval_tasks.get(step_order=2).status == "PENDING"

    request = service.LeaveRequestService.decide_request(
        request_id=request.pk,
        actor_user_id=8212,
        action="VERIFY",
    )
    assert request.status == "PENDING_SANCTION"

    request = service.LeaveRequestService.decide_request(
        request_id=request.pk,
        actor_user_id=8213,
        action="APPROVE",
    )
    balance = LeaveBalance.objects.get(
        user_id=4120, leave_type_code="EL", year=2026
    )
    assert request.status == "APPROVED"
    assert balance.used_days == Decimal("2")
    assert balance.reserved_days == Decimal("0")
    assert request.balance_events.filter(event_type="USE").count() == 1


@pytest.mark.django_db
def test_final_rejection_releases_reserved_balance(weekday_calendar, cl_policy):
    LeaveAuthorityRule.objects.create(
        department="Engineering",
        leave_type_code="CL",
        step_order=1,
        stage="UNIT_HEAD",
        decision_mode="FINAL",
        approver_user_id=8221,
    )
    request = submit_cl(4122, 5122)
    service.LeaveRequestService.respond_to_substitute(
        request_id=request.pk,
        actor_user_id=5122,
        action="ACCEPT",
    )
    request = service.LeaveRequestService.decide_request(
        request_id=request.pk,
        actor_user_id=8221,
        action="REJECT",
        reason="Not approved",
    )
    balance = LeaveBalance.objects.get(
        user_id=4122, leave_type_code="CL", year=2026
    )

    assert request.status == "REJECTED"
    assert balance.reserved_days == Decimal("0")
    assert balance.available_days == Decimal("8")
    assert request.balance_events.filter(event_type="RELEASE").count() == 1


@pytest.mark.django_db
def test_year_end_carries_lapses_and_converts_vl_idempotently(monkeypatch):
    from io import StringIO

    from django.core.management import call_command

    from modules.elm.models import LeaveBalanceEvent

    LeavePolicy.objects.update_or_create(
        leave_type_code="CL",
        defaults={
            "employee_kinds": ["staff"],
            "annual_entitlement": Decimal("8"),
            "annual_entitlement_by_kind": {"staff": "8.00"},
            "carries_forward": False,
        },
    )
    LeavePolicy.objects.update_or_create(
        leave_type_code="EL",
        defaults={
            "employee_kinds": ["faculty", "staff"],
            "annual_entitlement": Decimal("30"),
            "annual_entitlement_by_kind": {"faculty": "0.00", "staff": "30.00"},
            "carries_forward": True,
        },
    )
    LeavePolicy.objects.update_or_create(
        leave_type_code="VL",
        defaults={
            "employee_kinds": ["faculty"],
            "annual_entitlement": Decimal("60"),
            "annual_entitlement_by_kind": {"faculty": "60.00"},
            "carries_forward": False,
            "conversion_target_code": "EL",
            "conversion_divisor": Decimal("2"),
        },
    )
    LeaveBalance.objects.create(
        user_id=4201, leave_type_code="CL", year=2026,
        annual_credit=Decimal("8"), used_days=Decimal("2"),
    )
    LeaveBalance.objects.create(
        user_id=4202, leave_type_code="EL", year=2026,
        opening_balance=Decimal("1"), annual_credit=Decimal("30"),
        used_days=Decimal("5"),
    )
    LeaveBalance.objects.create(
        user_id=4110, leave_type_code="VL", year=2026,
        annual_credit=Decimal("60"), used_days=Decimal("59.50"),
    )

    def fake_directory(user_ids):
        return {
            user_id: SimpleNamespace(
                user_id=user_id,
                kind="faculty" if user_id == 4110 else "staff",
            )
            for user_id in user_ids
        }

    monkeypatch.setattr(
        "modules.elm.management.commands.process_leave_year_end.get_users",
        fake_directory,
    )
    call_command("process_leave_year_end", year=2026, stdout=StringIO())

    lapsed = LeaveBalance.objects.get(
        user_id=4201, leave_type_code="CL", year=2027
    )
    assert lapsed.opening_balance == Decimal("0")
    assert lapsed.annual_credit == Decimal("8")

    carried = LeaveBalance.objects.get(
        user_id=4202, leave_type_code="EL", year=2027
    )
    assert carried.opening_balance == Decimal("26")
    assert carried.annual_credit == Decimal("30")

    faculty_el = LeaveBalance.objects.get(
        user_id=4110, leave_type_code="EL", year=2027
    )
    assert faculty_el.opening_balance == Decimal("0.25")
    assert faculty_el.annual_credit == Decimal("0")
    old_vl = LeaveBalance.objects.get(
        user_id=4110, leave_type_code="VL", year=2026
    )
    assert old_vl.available_days == Decimal("0.00")

    call_command("process_leave_year_end", year=2026, stdout=StringIO())
    faculty_el.refresh_from_db()
    carried.refresh_from_db()
    assert faculty_el.opening_balance == Decimal("0.25")
    assert carried.opening_balance == Decimal("26")
    assert LeaveBalanceEvent.objects.filter(
        balance=old_vl,
        event_type="YEAR_END",
        note="Year-end output of VL for 2026",
    ).count() == 1
