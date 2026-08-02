"""Domain tests: pure Python, no database, milliseconds."""
import pytest

from modules.placement.domain import state_machine as sm
from modules.placement.domain.eligibility import evaluate

ALL = [sm.DRAFT, sm.SUBMITTED, sm.UNDER_REVIEW, sm.SHORTLISTED, sm.REJECTED,
       sm.WITHDRAWN, sm.OFFER_ISSUED, sm.OFFER_ACCEPTED, sm.OFFER_DECLINED]


def test_transition_table_is_the_specification():
    """Exhaustive 9x9 matrix: legal iff present in TRANSITIONS."""
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm in ALL:
        for to in ALL:
            assert sm.is_legal(frm, to) is ((frm, to) in declared)


def test_terminal_states_have_no_exits():
    for s in sm.TERMINAL:
        assert sm.allowed_targets(s) == []


def test_illegal_transition_raises():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.DRAFT, sm.OFFER_ACCEPTED)


def test_submitting_requires_eligibility_and_an_open_window():
    t = sm.resolve(sm.DRAFT, sm.SUBMITTED)
    assert "is_eligible" in t.guards
    assert "window_open" in t.guards


# ---- eligibility: the fail-closed table -------------------------------------
FACTS = {"cpi": 7.5, "discipline": "CSE", "active_backlogs": 0,
         "programme": "B.Tech", "is_placed": False}


def test_empty_rule_means_no_restriction():
    assert evaluate({}, FACTS).is_eligible is True


def test_simple_pass_and_fail():
    assert evaluate({"gte": ["cpi", 7.0]}, FACTS).is_eligible is True
    out = evaluate({"gte": ["cpi", 8.0]}, FACTS)
    assert out.is_eligible is False
    assert out.outcomes[0].reason == "cpi_out_of_range"


def test_unknown_field_denies():
    out = evaluate({"gte": ["gpa", 7.0]}, FACTS)      # 'gpa' is not a real field
    assert out.is_eligible is False
    assert out.error == "unknown_field"


def test_missing_fact_denies_rather_than_defaulting():
    out = evaluate({"gte": ["cpi", 7.0]}, {})
    assert out.is_eligible is False
    assert out.outcomes[0].reason == "missing_fact"


def test_no_declared_standing_is_not_cpi_zero():
    """A student with no declared result must be INELIGIBLE, not treated as 0.0
    — which would silently pass a `lte` rule."""
    assert evaluate({"lte": ["cpi", 5.0]}, {}).is_eligible is False


def test_all_any_not():
    assert evaluate({"all": [{"gte": ["cpi", 7.0]},
                             {"in": ["discipline", ["CSE", "ECE"]]}]},
                    FACTS).is_eligible is True
    assert evaluate({"any": [{"gte": ["cpi", 9.9]},
                             {"eq": ["discipline", "CSE"]}]},
                    FACTS).is_eligible is True
    assert evaluate({"not": {"eq": ["is_placed", True]}}, FACTS).is_eligible is True


def test_empty_any_denies():
    assert evaluate({"any": []}, FACTS).is_eligible is False


def test_failed_rules_are_reported_per_rule():
    out = evaluate({"all": [{"gte": ["cpi", 8.0]},
                            {"eq": ["active_backlogs", 0]}]}, FACTS)
    assert out.is_eligible is False
    assert [o.passed for o in out.outcomes] == [False, True]
