from datetime import date
from decimal import Decimal

import pytest

from modules.employee_leave.domain.workflow import (
    InvalidLeaveRequest,
    InvalidLeaveTransition,
    RequestFacts,
    charged_days,
    initial_state,
    transition,
    validate_extension,
)


def test_continuous_period_counts_inclusive_calendar_days():
    assert charged_days(date(2026, 10, 12), date(2026, 10, 14)) == Decimal("3")


def test_half_day_is_only_a_single_day_request():
    assert charged_days(date(2026, 10, 12), date(2026, 10, 12), half_day=True) == Decimal("0.5")
    with pytest.raises(InvalidLeaveRequest):
        charged_days(date(2026, 10, 12), date(2026, 10, 13), half_day=True)


def test_leave_routing_uses_category_and_substitute_gate():
    assert (
        initial_state(RequestFacts("CL", date(2026, 10, 12), date(2026, 10, 12)))
        == "unit_head_pending"
    )
    assert (
        initial_state(
            RequestFacts("EL", date(2026, 10, 12), date(2026, 10, 12), requires_substitute=True)
        )
        == "substitute_pending"
    )


def test_director_route_and_invalid_transition():
    facts = RequestFacts("EL", date(2026, 10, 12), date(2026, 10, 12), is_director=True)
    assert initial_state(facts) == "final_pending"
    assert transition("substitute_pending", "accept_substitute") == "unit_head_pending"
    with pytest.raises(InvalidLeaveTransition):
        transition("approved", "withdraw")


def test_higher_sanction_cancellation_stays_in_authority_order():
    assert (
        transition("cancellation_unit_head_pending", "route_cancellation_establishment")
        == "cancellation_establishment_pending"
    )
    assert (
        transition("cancellation_establishment_pending", "route_cancellation_final")
        == "cancellation_final_pending"
    )
    assert transition("cancellation_final_pending", "approve_cancellation") == "cancelled"


def test_only_supported_leave_categories_can_be_extended():
    validate_extension(leave_type="EL", start=date(2026, 10, 12), end=date(2026, 10, 14))
    with pytest.raises(InvalidLeaveRequest):
        validate_extension(leave_type="CL", start=date(2026, 10, 12), end=date(2026, 10, 14))
