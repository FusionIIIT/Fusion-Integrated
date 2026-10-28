"""Spec-driven ELM tests for the service layer (write path).

Phase 2 of the assignment: review, test, and improve the Phase-1 ELM
implementation against the ELM Specifications Bundle v1.4 FINAL.  These tests
are written from the Business Rule Specifications (v1.4), the Use Case
Specifications (v1.4), and the Workflow Specifications (v1.6) so that the exact
behaviours required by the spec are verified automatically.

Run:  .venv/Scripts/python.exe -m pytest modules/leave -q
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from conftest import make_session
from core.api.exceptions import ConflictError
from modules.leave.domain import state_machine as sm
from modules.leave.domain.categories import LeaveCategory
from modules.leave.models import (
    LeaveAccount,
    LeaveApplication,
)
from modules.leave.services import leave as svc

pytestmark = pytest.mark.django_db


# --- helpers -----------------------------------------------------------------

def _staff(uid=9):
    return make_session(user_id=uid, kind="staff",
                        permissions=frozenset({
                            "leave_management.leave.view",
                            "leave_management.leave.review",
                            "leave_management.leave.sanction",
                        }), modules=("leave_management",))


def _student(uid=1001):
    return make_session(user_id=uid, kind="student",
                        permissions=frozenset({
                            "leave_management.leave.apply",
                            "leave_management.leave.view_self",
                            "leave_management.leave.withdraw",
                            "leave_management.leave.cancel",
                            "leave_management.leave.extension",
                            "leave_management.leave.resumption",
                            "leave_management.substitute.respond",
                        }), modules=("leave_management",))


@pytest.fixture()
def el_account():
    """One employee with a full-year EL account, so balances behave deterministically."""
    return LeaveAccount.objects.create(
        user_id=1001, category=LeaveCategory.EL.value, year=2026,
        entitlement=Decimal("30"), carried_forward=Decimal("0"), availed=Decimal("0"))


# --- BR-EL-001 / BR-EL-002 / BR-EL-003 / BR-EL-004 / BR-EL-005 (entitlements) ---


class TestEntitlements:
    def test_apply_el_with_a_small_request_buys_part_of_the_year_balance(self, el_account):
        app = svc.apply_leave(principal=_student(), category="EL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10),
                              purpose="sick leave")
        assert app.leave_days == Decimal("10")
        assert LeaveAccount.objects.get(
            user_id=1001, category="EL").remaining == Decimal("30")

    def test_apply_more_than_fresh_balance_is_blocked(self, el_account):
        with pytest.raises(ConflictError):
            svc.apply_leave(principal=_student(), category="EL",
                            starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31),
                            purpose="too long")

    def test_half_day_cl_deducts_half_a_day(self, el_account):
        app = svc.apply_leave(principal=_student(), category="CL",
                              starts_on=date(2026, 8, 17), ends_on=date(2026, 8, 17),
                              half_day="first_half", purpose="doctor")
        assert app.leave_days == Decimal("0.5")
        svc.decide(application_id=app.id, principal=_staff(), actor_role="unit_head",
                   to_status=sm.SANCTIONED)
        assert LeaveAccount.objects.get(
            user_id=1001, category="CL").remaining == Decimal("7.5")


# --- BR-EL-010 / BR-EL-011 (continuous counting, weekends) -------------------


class TestCounting:
    def test_cl_counts_only_working_days(self, el_account):
        # BR-EL-011: CL does not count weekends, so a Mon-Tue-Wed window is
        # exactly 3 days, and never more than a fresh 8-day CL balance.
        app = svc.apply_leave(
            principal=_student(), category="CL",
            starts_on=date(2026, 1, 5), ends_on=date(2026, 1, 7),
            purpose="short"
        )
        assert app.leave_days == Decimal("3")
        assert LeaveAccount.objects.get(
            user_id=1001, category="CL").remaining == Decimal("8")


# --- BR-EL-012 / BR-EL-014 / BR-EL-015 (overlap, substitutes) ----------------


class TestOverlapAndSubstitute:
    def test_impermissible_overlap_blocked(self, el_account):
        svc.apply_leave(principal=_student(), category="EL",
                        starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10))
        with pytest.raises(ConflictError):
            svc.apply_leave(principal=_student(), category="EL",
                            starts_on=date(2026, 1, 5), ends_on=date(2026, 1, 15))

    def test_first_then_second_half_on_same_date_are_non_overlapping(self):
        svc.apply_leave(principal=_student(), category="CL",
                        starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 1),
                        half_day="first_half")
        app = svc.apply_leave(principal=_student(), category="CL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 1),
                              half_day="second_half")
        assert app.leave_days == Decimal("0.5")


# --- BR-EL-016 / BR-EL-017 / BR-EL-020 (unit head, higher sanction, director) -


class TestAuthority:
    def test_unit_head_cannot_sanction_higher_category_directly(self):
        app = svc.apply_leave(principal=_student(), category="EL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10))
        with pytest.raises(ConflictError):
            svc.decide(application_id=app.id, principal=_staff(),
                       actor_role="unit_head", to_status=sm.SANCTIONED)

    def test_director_self_sanction(self, el_account):
        app = svc.apply_leave(principal=_student(1002), category="EL",
                              starts_on=date(2026, 2, 1), ends_on=date(2026, 2, 10))
        svc.decide(application_id=app.id, principal=_staff(1002),
                   actor_role="sanctioning_authority", to_status=sm.SANCTIONED)
        assert LeaveApplication.objects.get(
            pk=app.id).status == sm.SANCTIONED


# --- BR-EL-022 / BR-EL-023 / BR-EL-024 (withdrawal, cancellation) ------------


class TestWithdrawal:
    def test_withdraw_pending(self, el_account):
        app = svc.apply_leave(principal=_student(), category="EL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10))
        svc.withdraw(application_id=app.id, principal=_student())
        db = LeaveApplication.objects.get(pk=app.id)
        assert db.status == sm.WITHDRAWN

    def test_withdraw_after_approval_blocked(self, el_account):
        app = svc.apply_leave(principal=_student(), category="EL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10))
        svc.decide(application_id=app.id, principal=_staff(), actor_role="sanctioning_authority",
                   to_status=sm.SANCTIONED)
        with pytest.raises(ConflictError):
            svc.withdraw(application_id=app.id, principal=_student())

    def test_withdraw_after_rejection_blocked(self, el_account):
        app = svc.apply_leave(principal=_student(), category="EL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10))
        svc.decide(application_id=app.id, principal=_staff(), actor_role="sanctioning_authority",
                   to_status=sm.REJECTED)
        db = LeaveApplication.objects.get(pk=app.id)
        assert db.status == sm.REJECTED
        with pytest.raises(ConflictError):
            svc.withdraw(application_id=app.id, principal=_student())


# --- BR-EL-023, BW-EL-10 / BW-EL-11 (cancellation restores the deduction) ----


class TestCancellation:
    def test_cancellation_request_allowed_only_before_start(self, el_account):
        app = svc.apply_leave(principal=_student(), category="EL",
                              starts_on=date(2026, 1, 1), ends_on=date(2026, 1, 10))
        svc.decide(application_id=app.id, principal=_staff(), actor_role="sanctioning_authority",
                   to_status=sm.SANCTIONED)
        # request_cancellation must be allowed only before the start date.
        with pytest.raises(ConflictError):
            svc.request_cancellation(application_id=app.id, principal=_student(),
                                     reason="moved")
