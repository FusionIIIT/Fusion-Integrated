"""Every branch of every pure rule, with no database."""
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest

from modules.gymkhana.domain import rules
from modules.gymkhana.domain.rules import RuleViolation, Slot, Target

TODAY = date(2026, 11, 22)


def code(fn, *args):
    with pytest.raises(RuleViolation) as exc:
        fn(*args)
    return exc.value.code


@pytest.mark.parametrize("raw,clean", [("Technical", "technical"), (" sports ", "sports"),
                                       ("CULTURAL", "cultural")])
def test_br_gym_003_allowed_categories_are_accepted(raw, clean):
    assert rules.check_category(raw) == clean


@pytest.mark.parametrize("raw", ["Literary", "", None])
def test_br_gym_003_any_other_category_is_refused(raw):
    assert code(rules.check_category, raw) == "invalid_category"


def test_coordinator_and_co_coordinator_must_differ():
    assert code(rules.check_distinct_leaders, 1, 1) == "same_leader_twice"
    rules.check_distinct_leaders(1, 2)


def test_br_gym_005_start_must_precede_end():
    rules.check_time_range(time(10), time(11))
    assert code(rules.check_time_range, time(11), time(11)) == "invalid_time_range"
    assert code(rules.check_time_range, time(12), time(11)) == "invalid_time_range"


def test_booking_date_window():
    rules.check_booking_date(TODAY, TODAY)
    rules.check_booking_date(TODAY + timedelta(days=365), TODAY)
    assert code(rules.check_booking_date, TODAY - timedelta(days=1), TODAY) == "booking_in_past"
    assert code(rules.check_booking_date, TODAY + timedelta(days=366),
                TODAY) == "booking_too_far_ahead"


@pytest.mark.parametrize("a,b,clash", [
    ((10, 11), (11, 12), False),     # BR-GYM-006: half-open, touching is fine
    ((10, 11), (9, 10), False),
    ((10, 12), (11, 13), True),
    ((10, 12), (10, 12), True),
    ((10, 13), (11, 12), True),
    ((11, 12), (10, 13), True),
])
def test_br_gym_006_overlap_is_half_open(a, b, clash):
    assert rules.overlaps(time(a[0]), time(a[1]), time(b[0]), time(b[1])) is clash


def test_br_gym_006_find_conflict_returns_the_clashing_slot():
    slots = [Slot(1, time(8), time(9)), Slot(2, time(10), time(12))]
    assert rules.find_conflict(time(11), time(13), slots).booking_id == 2
    assert rules.find_conflict(time(9), time(10), slots) is None


def test_br_gym_017_amount_is_zero_or_more():
    rules.check_amount(Decimal("0"))
    rules.check_amount(Decimal("10.50"))
    assert code(rules.check_amount, Decimal("-0.01")) == "negative_amount"


def test_br_gym_012_choices():
    assert rules.check_choices([" A ", "B"]) == ["A", "B"]
    assert code(rules.check_choices, ["A"]) == "too_few_choices"
    assert code(rules.check_choices, []) == "too_few_choices"
    assert code(rules.check_choices, ["A", " "]) == "empty_choice"
    assert code(rules.check_choices, ["A", "a"]) == "duplicate_choice"
    assert code(rules.check_choices, [str(i) for i in range(11)]) == "too_many_choices"


def test_br_gym_013_targets():
    assert rules.check_targets([Target(2023, " CSE ")]) == [Target(2023, "CSE")]
    assert code(rules.check_targets, []) == "no_targets"
    assert code(rules.check_targets, [Target(1999)]) == "invalid_target"
    assert code(rules.check_targets, [Target(2023, "x" * 41)]) == "invalid_target"
    assert code(rules.check_targets, [Target(2023, "CSE"), Target(2023, "cse")]) \
        == "duplicate_target"
    assert code(rules.check_targets, [Target(2000 + i) for i in range(21)]) \
        == "too_many_targets"


def test_poll_expiry_cannot_be_in_the_past():
    rules.check_expiry(TODAY, TODAY)
    assert code(rules.check_expiry, TODAY - timedelta(days=1), TODAY) == "expiry_in_past"


def test_br_gym_014_poll_is_active_through_its_expiry_day():
    assert rules.poll_is_active(TODAY, TODAY)
    assert not rules.poll_is_active(TODAY - timedelta(days=1), TODAY)


@pytest.mark.parametrize("targets,batch,disc,ok", [
    ([Target(2023, "CSE")], 2023, "cse", True),
    ([Target(2023, "CSE")], 2023, "ECE", False),
    ([Target(2023, "CSE")], 2024, "CSE", False),
    ([Target(2023, "")], 2023, "ECE", True),      # all branches of the batch
    ([Target(2023, "")], 2023, "", True),
    ([Target(2023, "CSE")], 2023, "", False),
    ([Target(2023, "")], None, "CSE", False),     # no batch on record: fail closed
    ([], 2023, "CSE", False),
])
def test_br_gym_013_audience(targets, batch, disc, ok):
    assert rules.in_audience(targets, batch, disc) is ok


def test_report_event_must_have_happened():
    now = datetime(2026, 11, 22, 12, tzinfo=UTC)
    rules.check_event_held(now, now)
    assert code(rules.check_event_held, now + timedelta(minutes=1), now) \
        == "event_not_yet_held"


def test_a_conflict_violation_is_marked_as_such():
    with pytest.raises(RuleViolation) as exc:
        rules.check_booking_date(TODAY - timedelta(days=1), TODAY)
    assert exc.value.conflict and exc.value.field == "date"
