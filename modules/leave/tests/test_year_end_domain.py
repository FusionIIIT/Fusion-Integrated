from dataclasses import replace
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain.policy import Policy
from modules.leave.domain.year_end import Balance, plan


def make_balance(category, days):
    return Balance(user_id=1, category=category, days=Decimal(str(days)))


def test_faculty_vacation_converts_to_earned_leave():
    outcomes = plan(
        Policy(),
        cat.FACULTY,
        [make_balance(cat.VACATION, 10)],
        2026,
    )

    assert [(o.category, o.kind, o.days) for o in outcomes] == [
        (cat.VACATION, "lapse", Decimal("10")),
        (cat.EARNED, "conversion", Decimal("5.00")),
    ]


def test_staff_vacation_lapses_without_conversion():
    outcomes = plan(
        Policy(),
        cat.STAFF,
        [make_balance(cat.VACATION, 10)],
        2026,
    )

    assert len(outcomes) == 1
    assert outcomes[0].kind == "lapse"
    assert outcomes[0].days == Decimal("10")


def test_earned_leave_carries_forward_without_a_cap():
    outcomes = plan(
        Policy(),
        cat.STAFF,
        [make_balance(cat.EARNED, 12)],
        2026,
    )

    assert len(outcomes) == 1
    assert outcomes[0].kind == "carry_forward"
    assert outcomes[0].days == Decimal("12")


def test_earned_leave_above_cap_is_partly_lapsed():
    policy = replace(Policy(), earned_carry_forward_cap=Decimal("8"))

    outcomes = plan(
        policy,
        cat.STAFF,
        [make_balance(cat.EARNED, 12)],
        2026,
    )

    assert [(o.kind, o.days) for o in outcomes] == [
        ("carry_forward", Decimal("8")),
        ("lapse", Decimal("4")),
    ]


def test_casual_leave_lapses():
    outcomes = plan(
        Policy(),
        cat.STAFF,
        [make_balance(cat.CASUAL, 5)],
        2026,
    )

    assert len(outcomes) == 1
    assert outcomes[0].kind == "lapse"
    assert outcomes[0].days == Decimal("5")


def test_zero_and_negative_balances_produce_no_outcomes():
    outcomes = plan(
        Policy(),
        cat.STAFF,
        [
            make_balance(cat.EARNED, 0),
            make_balance(cat.CASUAL, -3),
        ],
        2026,
    )

    assert outcomes == []
