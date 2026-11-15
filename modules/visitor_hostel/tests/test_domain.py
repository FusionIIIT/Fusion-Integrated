"""The rules with no database: every branch, in milliseconds."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from modules.visitor_hostel.domain import (
    billing,
    cancellation,
    inventory,
    meals,
    requisition,
    tariffs,
)
from modules.visitor_hostel.domain import duty as duty_rules
from modules.visitor_hostel.domain import state_machine as sm

ARRIVAL = date(2026, 12, 10)


# -- Cancellation schedule (BR-VH-006..009) ------------------------------------
@pytest.mark.parametrize(("days_before", "code", "percent"), [
    (0, "same_day", 50),            # BR-VH-009 takes precedence over "within 7"
    (1, "within_seven_days", 25),
    (6, "within_seven_days", 25),   # BR-VH-008
    (7, "seven_days", 0),           # BR-VH-007
    (8, "beyond_schedule", 0),      # not stated by the source; flagged
    (60, "beyond_schedule", 0),
])
def test_the_schedule_row_for_each_distance(days_before, code, percent):
    case = cancellation.case_for(ARRIVAL, ARRIVAL - timedelta(days=days_before))
    assert (case.code, case.percent) == (code, Decimal(percent))


def test_only_the_unstated_case_is_flagged_for_clarification():
    flagged = {c.code for c in cancellation.CASES.values() if c.needs_clarification}
    assert flagged == {"beyond_schedule"}


def test_a_request_after_the_arrival_date_is_not_pre_arrival():
    with pytest.raises(cancellation.NotBeforeArrival):
        cancellation.case_for(ARRIVAL, ARRIVAL + timedelta(days=1))


def test_charges_are_a_percentage_of_one_day_rounded_to_the_paisa():
    assert cancellation.charge(cancellation.WITHIN_SEVEN_DAYS, Decimal("1333.33")) \
        == Decimal("333.33")
    assert cancellation.charge(cancellation.NO_SHOW, Decimal("1001")) == Decimal("500.50")


def test_a_free_case_needs_no_rent_and_a_paid_one_does():
    assert cancellation.charge(cancellation.SEVEN_DAYS, None) == Decimal("0.00")
    with pytest.raises(ValueError):
        cancellation.charge(cancellation.SAME_DAY, None)


# -- State machine -------------------------------------------------------------
LANES = (sm.INDENTER, sm.CARETAKER, sm.INCHARGE, sm.SYSTEM)


@pytest.mark.parametrize("frm", sm.ALL_STATES)
@pytest.mark.parametrize("to", sm.ALL_STATES)
def test_every_pair_not_in_the_table_is_refused(frm, to):
    if sm.is_legal(frm, to):
        return
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(frm, to)


@pytest.mark.parametrize("t", sm.TRANSITIONS, ids=lambda t: f"{t.frm}->{t.to}")
def test_every_edge_refuses_every_other_lane(t):
    for lane in set(LANES) - t.actors:
        with pytest.raises(sm.ActorNotAllowed):
            sm.resolve(t.frm, t.to, lane)


def test_terminal_states_have_no_way_out():
    assert not [t for t in sm.TRANSITIONS if t.frm in sm.TERMINAL]


def test_rooms_are_allotted_only_from_approved():
    """BR-VH-012, as a property of the table."""
    assert {t.frm for t in sm.TRANSITIONS if t.to == sm.ROOM_ALLOTTED} == {sm.APPROVED}


def test_the_caretaker_cannot_approve_and_the_incharge_cannot_forward():
    assert sm.APPROVED not in sm.allowed_targets(sm.FORWARDED, sm.CARETAKER)
    assert sm.allowed_targets(sm.PENDING, sm.INCHARGE) == []


def test_the_indenter_moves_nothing_through_the_table():
    """Cancellation and modification are requests, decided by an officer."""
    assert not [t for t in sm.TRANSITIONS if sm.INDENTER in t.actors]


def test_cancellation_is_reachable_from_every_pre_arrival_state_only():
    assert {t.frm for t in sm.TRANSITIONS if t.to == sm.CANCELLED} == sm.PRE_ARRIVAL


# -- Tariffs (BR-VH-019, BR-VH-023) --------------------------------------------
def _rows():
    return [
        tariffs.TariffRow(1, tariffs.room_key("A", "single"), Decimal("1000"), date(2026, 1, 1)),
        tariffs.TariffRow(2, tariffs.room_key("A", "single"), Decimal("1200"), date(2026, 7, 1)),
        tariffs.TariffRow(3, tariffs.room_key("A", "double"), Decimal("1500"), date(2026, 1, 1)),
    ]


def test_the_latest_tariff_already_in_force_is_selected():
    key = tariffs.room_key("A", "single")
    assert tariffs.select(_rows(), key=key, on=date(2026, 6, 30)).rate == Decimal("1000")
    assert tariffs.select(_rows(), key=key, on=date(2026, 7, 1)).rate == Decimal("1200")


def test_no_tariff_in_force_is_an_error_not_a_zero():
    with pytest.raises(tariffs.NoApplicableTariff):
        tariffs.select(_rows(), key=tariffs.room_key("A", "single"), on=date(2025, 12, 31))


@pytest.mark.parametrize(("category", "occupancy"), [("E", "single"), ("A", "triple")])
def test_only_the_stated_categories_and_occupancies_exist(category, occupancy):
    with pytest.raises(ValueError):
        tariffs.room_key(category, occupancy)


# -- Meals (BR-VH-029..031) ----------------------------------------------------
@pytest.mark.parametrize(("kind", "item", "priced"), [
    ("full_day", "", "full_day"), ("individual", "breakfast", "breakfast"),
    ("individual", "dinner", "dinner"), ("add_on", "tea", "tea"), ("add_on", "milk", "milk"),
])
def test_the_stated_meal_options_are_accepted(kind, item, priced):
    assert meals.priced_item(kind, item) == priced


@pytest.mark.parametrize(("kind", "item"), [
    ("individual", "tea"), ("individual", "snacks"), ("add_on", "lunch"),
    ("add_on", "coffee"), ("full_day", "lunch"), ("buffet", ""),
])
def test_anything_else_is_refused(kind, item):
    with pytest.raises(meals.InvalidMeal):
        meals.priced_item(kind, item)


def test_a_meal_must_fall_inside_the_stay():
    meals.within_stay(date(2026, 1, 2), date(2026, 1, 1), date(2026, 1, 3))
    with pytest.raises(meals.InvalidMeal):
        meals.within_stay(date(2026, 1, 4), date(2026, 1, 1), date(2026, 1, 3))


# -- Billing arithmetic (BR-VH-033..035) ---------------------------------------
def test_a_same_day_stay_is_charged_one_day():
    assert billing.nights(date(2026, 1, 1), date(2026, 1, 1)) == 1
    assert billing.nights(date(2026, 1, 1), date(2026, 1, 4)) == 3


def test_room_lines_use_the_rate_in_force_on_check_in():
    lines = billing.room_lines([("101", "single"), ("102", "double")], category="A",
                               check_in=date(2026, 6, 29), check_out=date(2026, 7, 2),
                               rates=_rows())
    assert [ln.amount for ln in lines] == [Decimal("3000.00"), Decimal("4500.00")]
    assert billing.totals(lines).total == Decimal("7500.00")


def test_one_day_rent_sums_every_room():
    assert billing.one_day_rent(["single", "double"], category="A", on=date(2026, 3, 1),
                                rates=_rows()) == Decimal("2500.00")


# -- Requisition (BR-VH-002) and inventory (BR-VH-041) -------------------------
def _valid(**over):
    base = {"category": "A", "occupancy": "single", "billing_responsibility": "project",
            "arrival_date": date(2026, 5, 2), "departure_date": date(2026, 5, 3),
            "rooms_required": 1, "occupants": 1, "today": date(2026, 5, 1)}
    return {**base, **over}


def test_a_complete_requisition_passes():
    requisition.validate(**_valid())


@pytest.mark.parametrize(("over", "code"), [
    ({"billing_responsibility": "department"}, "invalid_billing_responsibility"),
    ({"category": "Z"}, "invalid_category"),
    ({"arrival_date": date(2026, 4, 30)}, "arrival_in_past"),
    ({"departure_date": date(2026, 5, 1)}, "departure_before_arrival"),
    ({"rooms_required": 0}, "no_rooms"),
])
def test_a_bad_requisition_names_what_is_wrong(over, code):
    with pytest.raises(requisition.InvalidRequisition) as exc:
        requisition.validate(**_valid(**over))
    assert exc.value.code == code


def test_at_the_threshold_is_not_below_it():
    assert inventory.is_below_threshold(4, 5)
    assert not inventory.is_below_threshold(5, 5)


def test_stock_cannot_go_negative():
    assert inventory.apply_delta(3, -3) == 0
    with pytest.raises(inventory.NegativeStock):
        inventory.apply_delta(3, -4)


def test_a_duty_assignment_must_end_after_it_starts():
    start = datetime(2026, 1, 1)
    duty_rules.validate_window(start, start + timedelta(days=1))
    with pytest.raises(duty_rules.InvalidDutyWindow):
        duty_rules.validate_window(start, start)
