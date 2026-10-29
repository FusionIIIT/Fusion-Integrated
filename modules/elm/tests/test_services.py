"""Tests for ELM services and state transitions with database models."""
import datetime
from decimal import Decimal
import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveTransition
from modules.elm.services import balances as balance_service
from modules.elm.services import leave_service


class DummyPrincipal:
    """Mock principal for testing service authorization."""
    def __init__(self, user_id: int, permissions: list[str] | None = None, is_superuser: bool = False):
        self.user_id = user_id
        self.permissions = set(permissions or [])
        self.is_superuser = is_superuser

    def has_permission(self, code: str) -> bool:
        return self.is_superuser or code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return self.is_superuser or bool(self.permissions.intersection(codes))


@pytest.mark.django_db
def test_create_and_submit_cl():
    emp = DummyPrincipal(user_id=101, permissions=["elm.leave.apply", "elm.leave.view_self"])
    unit_head = DummyPrincipal(user_id=201, permissions=["elm.leave.approve"])

    # Credit balance
    balance_service.credit_annual_entitlement(user_id=101, year=2026, is_faculty=False)

    # 1. Apply for 1 day CL on a Monday
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 2)
    req = leave_service.create_leave_request(
        actor=emp,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Personal errand",
        submit=True,
    )

    assert req.status == sm.AWAITING_UNIT_HEAD
    assert req.days_counted == Decimal("1.0")

    # 2. Unit Head approves directly (BR-EL-016)
    approved_req = leave_service.review_unit_head(
        actor=unit_head,
        request_id=req.pk,
        action="approve",
        reason="Granted",
    )
    assert approved_req.status == sm.APPROVED
    assert approved_req.approved_at is not None

    # Check balance deducted: 8 - 1 = 7 available
    bal = LeaveBalance.objects.get(user_id=101, category="CL", year=2026)
    assert bal.used == Decimal("1.0")
    assert bal.available == 7.0


@pytest.mark.django_db
def test_cw_el_01_full_workflow_with_substitute_and_sanction():
    emp = DummyPrincipal(user_id=102, permissions=["elm.leave.apply"])
    sub = DummyPrincipal(user_id=103, permissions=["elm.leave.respond_substitute"])
    uh = DummyPrincipal(user_id=202, permissions=["elm.leave.approve"])
    sanctioner = DummyPrincipal(user_id=301, permissions=["elm.leave.approve", "elm.leave.report"])

    # Credit EL balance
    balance_service.credit_annual_entitlement(user_id=102, year=2026, is_faculty=False)

    # Apply for EL (requires substitute)
    start = datetime.date(2026, 11, 9)  # Mon
    end = datetime.date(2026, 11, 13)   # Fri
    req = leave_service.create_leave_request(
        actor=emp,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Annual vacation",
        substitute_id=103,
        submit=True,
    )
    assert req.status == sm.AWAITING_SUBSTITUTE
    assert req.days_counted == Decimal("5.0")

    # Substitute accepts
    req = leave_service.respond_substitute(actor=sub, request_id=req.pk, accept=True)
    assert req.status == sm.AWAITING_UNIT_HEAD
    assert req.substitute_accepted is True

    # Unit Head recommends
    req = leave_service.review_unit_head(actor=uh, request_id=req.pk, action="recommend", reason="Recommended")
    assert req.status == sm.AWAITING_SANCTION
    assert req.unit_head_recommendation == "recommended"

    # Sanction Authority approves
    req = leave_service.sanction_leave(actor=sanctioner, request_id=req.pk, approve=True)
    assert req.status == sm.APPROVED

    bal = LeaveBalance.objects.get(user_id=102, category="EL", year=2026)
    assert bal.used == Decimal("5.0")
    assert bal.available == 25.0


@pytest.mark.django_db
def test_substitute_decline_returns_to_draft():
    emp = DummyPrincipal(user_id=104, permissions=["elm.leave.apply"])
    sub = DummyPrincipal(user_id=105, permissions=["elm.leave.respond_substitute"])

    balance_service.credit_annual_entitlement(user_id=104, year=2026, is_faculty=False)

    req = leave_service.create_leave_request(
        actor=emp,
        category="EL",
        start_date=datetime.date(2026, 11, 16),
        end_date=datetime.date(2026, 11, 18),
        substitute_id=105,
        submit=True,
    )
    assert req.status == sm.AWAITING_SUBSTITUTE

    # Substitute declines
    req = leave_service.respond_substitute(actor=sub, request_id=req.pk, accept=False, reason="Too busy with exams")
    assert req.status == sm.DRAFT
    assert req.substitute_accepted is False


@pytest.mark.django_db
def test_cw_el_02_cancellation_and_balance_refund():
    emp = DummyPrincipal(user_id=106, permissions=["elm.leave.apply", "elm.leave.cancel"])
    sanctioner = DummyPrincipal(user_id=301, permissions=["elm.leave.approve", "elm.leave.report"])

    balance_service.credit_annual_entitlement(user_id=106, year=2026, is_faculty=False)

    # Far future leave
    start = datetime.date(2026, 12, 1)
    end = datetime.date(2026, 12, 4)
    req = leave_service.create_leave_request(
        actor=emp,
        category="EL",
        start_date=start,
        end_date=end,
        substitute_id=105,
        submit=True,
    )
    # Directly transition through approval for test
    req.status = sm.AWAITING_SANCTION
    req.save()
    req = leave_service.sanction_leave(actor=sanctioner, request_id=req.pk, approve=True)
    assert req.status == sm.APPROVED
    assert LeaveBalance.objects.get(user_id=106, category="EL", year=2026).used == Decimal("4.0")

    # Request cancellation
    req = leave_service.request_cancellation(actor=emp, request_id=req.pk, reason="Plans changed")
    assert req.status == sm.CANCEL_REQUESTED

    # Sanctioner approves cancellation -> refunds balance!
    req = leave_service.decide_cancellation(actor=sanctioner, request_id=req.pk, approve=True)
    assert req.status == sm.CANCELLED

    bal = LeaveBalance.objects.get(user_id=106, category="EL", year=2026)
    assert bal.used == Decimal("0.0")
    assert bal.available == 30.0


@pytest.mark.django_db
def test_cw_el_04_duty_resumption_early_return_refunds_days():
    emp = DummyPrincipal(user_id=107, permissions=["elm.leave.apply", "elm.leave.modify"])
    sanctioner = DummyPrincipal(user_id=301, permissions=["elm.leave.approve", "elm.leave.report"])

    balance_service.credit_annual_entitlement(user_id=107, year=2026, is_faculty=False)

    # 5 days EL: Mon Nov 2 to Fri Nov 6
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)
    req = leave_service.create_leave_request(actor=emp, category="EL", start_date=start, end_date=end, submit=True)
    req.status = sm.AWAITING_SANCTION
    req.save()
    req = leave_service.sanction_leave(actor=sanctioner, request_id=req.pk, approve=True)
    assert req.days_counted == Decimal("5.0")

    # Returned 2 days early on Thursday Nov 5 (actual leave was Mon-Wed = 3 days)
    resumption_date = datetime.date(2026, 11, 5)
    req = leave_service.submit_resumption(actor=emp, request_id=req.pk, resumption_date=resumption_date)
    assert req.status == sm.RESUMPTION_SUBMITTED

    req = leave_service.review_resumption(actor=sanctioner, request_id=req.pk)
    assert req.status == sm.RESUMPTION_REVIEWED
    assert req.days_counted == Decimal("3.0")

    # Check 2 unused days refunded: used should be 3.0, available 27.0
    bal = LeaveBalance.objects.get(user_id=107, category="EL", year=2026)
    assert bal.used == Decimal("3.0")
    assert bal.available == 27.0


@pytest.mark.django_db
def test_year_end_rollover_faculty_vl_and_non_faculty_el():
    # 1. Non-faculty EL rollover: 10 used, 20 carried forward
    balance_service.credit_annual_entitlement(user_id=501, year=2025, is_faculty=False)
    balance_service.deduct_leave_balance(user_id=501, category="EL", year=2025, days=Decimal("10.0"))

    bals_2026 = balance_service.process_year_end_rollover(user_id=501, from_year=2025, to_year=2026, is_faculty=False)
    el_2026 = bals_2026["EL"]
    assert el_2026.credited == Decimal("30.0")
    assert el_2026.carried_forward == Decimal("20.0")
    assert el_2026.available == 50.0

    # 2. Faculty VL to EL conversion (BR-EL-008): 60 VL unused -> 30 EL credited
    balance_service.credit_annual_entitlement(user_id=502, year=2025, is_faculty=True)
    fac_2026 = balance_service.process_year_end_rollover(user_id=502, from_year=2025, to_year=2026, is_faculty=True)
    fac_el_2026 = fac_2026["EL"]
    assert fac_el_2026.carried_forward == Decimal("30.0")  # 60 / 2 = 30 EL
    assert fac_el_2026.available == 30.0
