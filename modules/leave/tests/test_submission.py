"""Submitting a request: what the validation refuses, and where it routes."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Half
from modules.leave.domain.state_machine import State
from modules.leave.selectors import balances
from modules.leave.services import requests as service
from modules.leave.tests.factories import credit, setup_all

pytestmark = pytest.mark.django_db

USER = 501
D = Decimal


@pytest.fixture
def configured():
    return setup_all(USER)


def apply_cl(day=date(2026, 9, 1), **kw):
    return service.submit(
        user_id=kw.pop("user_id", USER),
        category=kw.pop("category", Category.CL),
        starts_on=day,
        ends_on=kw.pop("ends_on", day),
        reason="personal",
        faculty=kw.pop("faculty", False),
        **kw,
    )


class TestRouting:
    def test_casual_leave_goes_straight_to_the_unit_head(self, configured):
        # BR-EL-016. Unit head is final, so there is no establishment step.
        r = apply_cl()
        assert r.state == State.AWAITING_UNIT_HEAD.value

    def test_a_substitute_is_asked_before_the_unit_head(self, configured):
        r = apply_cl(substitute_user_id=777)
        assert r.state == State.AWAITING_SUBSTITUTE.value
        assert r.nominations.count() == 1

    def test_submission_is_recorded_in_the_trail(self, configured):
        r = apply_cl()
        move = r.transitions.get()
        assert (move.from_state, move.to_state) == (
            State.DRAFT.value,
            State.AWAITING_UNIT_HEAD.value,
        )
        assert move.workflow_ref


class TestValidation:
    def test_a_backwards_period_is_refused(self, configured):
        with pytest.raises(BadRequestError):
            apply_cl(date(2026, 9, 10), ends_on=date(2026, 9, 1))

    def test_a_half_day_is_refused_for_earned_leave(self, configured):
        # BR-EL-010. Half days are a casual-leave affair.
        with pytest.raises(BadRequestError):
            apply_cl(category=Category.EL, half=Half.FIRST)

    def test_more_days_than_the_balance_is_refused(self, configured):
        with pytest.raises(ConflictError) as exc:
            service.submit(
                user_id=USER,
                category=Category.CL,
                starts_on=date(2026, 9, 1),
                ends_on=date(2026, 9, 30),
                reason="long",
                faculty=False,
            )
        assert exc.value.code == "insufficient_balance"

    def test_overlapping_leave_is_refused(self, configured):
        apply_cl(date(2026, 9, 1))
        with pytest.raises(ConflictError) as exc:
            apply_cl(date(2026, 9, 1))
        assert exc.value.code == "overlapping_leave"

    def test_opposite_halves_of_one_day_are_permitted(self, configured):
        # BR-EL-012. The one case where a date may be shared.
        apply_cl(date(2026, 9, 1), half=Half.FIRST)
        second = apply_cl(date(2026, 9, 1), half=Half.SECOND)
        assert second.requested_days == D("0.5")

    def test_nobody_may_stand_in_for_themselves(self, configured):
        with pytest.raises(BadRequestError) as exc:
            apply_cl(substitute_user_id=USER)
        assert exc.value.code == "substitute_is_applicant"

    def test_a_restricted_holiday_must_name_a_published_date(self, configured):
        with pytest.raises(BadRequestError) as exc:
            apply_cl(date(2026, 9, 3), category=Category.RH)
        assert exc.value.code == "rh_date_invalid"

    def test_a_published_restricted_holiday_is_accepted(self, configured):
        credit(USER, Category.RH, 2)
        r = apply_cl(date(2026, 10, 2), category=Category.RH)
        assert r.requested_days == D(1)

    def test_vacation_leave_outside_the_window_is_refused(self, configured):
        credit(USER, Category.VL, 60)
        with pytest.raises(BadRequestError) as exc:
            service.submit(
                user_id=USER,
                category=Category.VL,
                starts_on=date(2026, 9, 1),
                ends_on=date(2026, 9, 5),
                reason="break",
                faculty=True,
            )
        assert exc.value.code == "outside_vacation_period"

    def test_vacation_leave_inside_the_window_is_accepted(self, configured):
        credit(USER, Category.VL, 60)
        r = service.submit(
            user_id=USER,
            category=Category.VL,
            starts_on=date(2026, 6, 1),
            ends_on=date(2026, 6, 7),
            reason="break",
            faculty=True,
        )
        # BR-EL-011. Vacation leave counts continuously, so seven calendar days.
        assert r.requested_days == D(7)


class TestCounting:
    def test_earned_leave_charges_the_intervening_weekend(self, configured):
        r = service.submit(
            user_id=USER,
            category=Category.EL,
            starts_on=date(2026, 8, 10),
            ends_on=date(2026, 8, 17),
            reason="travel",
            faculty=False,
        )
        assert r.requested_days == D(8)

    def test_casual_leave_charges_only_working_days(self, configured):
        r = service.submit(
            user_id=USER,
            category=Category.CL,
            starts_on=date(2026, 8, 10),
            ends_on=date(2026, 8, 17),
            reason="travel",
            faculty=False,
        )
        # 15 August is a closed holiday and the weekend does not count.
        assert r.requested_days == D(6)

    def test_the_balance_is_untouched_until_the_leave_is_approved(self, configured):
        before = balances.available(USER, 2026, Category.CL)
        apply_cl()
        assert balances.available(USER, 2026, Category.CL) == before
