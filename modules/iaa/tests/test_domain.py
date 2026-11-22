"""The pure rules: state tables, policy shape, routing, validation and budget arithmetic.

No database here: these are the decisions the services lean on (IAA-BR-001..006, 101..104).
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.iaa.domain import budget, roles, routing
from modules.iaa.domain import policy as policy_rules
from modules.iaa.domain import state_machine as sm
from modules.iaa.domain.validation import Submission, submission_errors
from modules.iaa.tests.helpers import POLICY

HOD, DEAN, DIRECTOR = roles.HOD, roles.DEAN, roles.DIRECTOR


# ── state machines ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("t", sm.RECORD_TRANSITIONS, ids=lambda t: f"{t.kind}:{t.frm}:{t.event}")
def test_every_record_transition_is_reachable_by_its_actor_only(t):
    assert sm.resolve_record(t.kind, t.frm, t.event, t.actor) == t
    wrong = next(a for a in (roles.OWNER, roles.FINANCE_ACTOR, roles.APPROVER_ACTOR,
                             roles.AUDITOR_ACTOR) if a != t.actor)
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve_record(t.kind, t.frm, t.event, wrong)


def test_a_terminal_record_state_has_no_way_out():
    for kind in sm.KINDS:
        for state in sm.RECORD_TERMINAL:
            assert sm.record_events(kind, state) == []


def test_every_record_state_is_declared():
    for t in sm.RECORD_TRANSITIONS:
        assert t.frm in sm.RECORD_STATES and t.to in sm.RECORD_STATES


def test_a_state_that_skips_a_step_is_refused():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve_record(sm.EXPENSE, sm.DRAFT, sm.APPROVE_FINAL, roles.APPROVER_ACTOR)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve_record(sm.EXPENSE, sm.SUBMITTED, sm.RECORD, roles.FINANCE_ACTOR)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve_record(sm.EXPENSE, sm.REJECTED, sm.SUBMIT, roles.OWNER)


def test_a_ta_claim_is_never_a_draft_and_an_expense_has_no_verify():
    assert sm.record_events(sm.TA, sm.DRAFT) == []
    assert sm.VERIFY not in sm.record_events(sm.EXPENSE, sm.SUBMITTED)
    assert sm.VALIDATE not in sm.record_events(sm.TA, sm.SUBMITTED)


def test_only_the_system_escalates_and_only_a_pending_authority_item():
    for kind in sm.KINDS:
        for state in sm.RECORD_STATES:
            assert sm.ESCALATE not in sm.record_events(kind, state, roles.FINANCE_ACTOR)
    assert sm.ESCALATE in sm.record_events(sm.EXPENSE, sm.APPROVAL_PENDING, roles.SYSTEM)
    assert sm.ESCALATE not in sm.record_events(sm.EXPENSE, sm.ESCALATED, roles.SYSTEM)


def test_an_authority_item_is_recorded_only_by_finance_after_approval():
    assert sm.record_events(sm.EXPENSE, sm.APPROVED, roles.FINANCE_ACTOR) == [sm.RECORD]
    assert sm.record_events(sm.TA, sm.VERIFIED, roles.FINANCE_ACTOR) == [sm.RECORD]
    assert sm.record_events(sm.EXPENSE, sm.FINANCE_VALIDATED, roles.FINANCE_ACTOR) == []


def test_anomaly_lifecycle_and_its_dead_end():
    assert sm.resolve_anomaly(sm.ANOMALY_OPEN, sm.RESOLVE).to == sm.ANOMALY_RESOLVED
    assert sm.resolve_anomaly(sm.ANOMALY_OPEN, sm.ESCALATE).to == sm.ANOMALY_ESCALATED
    assert sm.resolve_anomaly(sm.ANOMALY_ESCALATED, sm.RESOLVE).to == sm.ANOMALY_RESOLVED
    for event in (sm.RESOLVE, sm.ESCALATE):
        with pytest.raises(sm.InvalidTransition):
            sm.resolve_anomaly(sm.ANOMALY_RESOLVED, event)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve_anomaly(sm.ANOMALY_ESCALATED, sm.ESCALATE)


def test_observation_lifecycle_closes_only_after_a_response_and_by_the_auditor():
    assert sm.resolve_observation(sm.OBS_OPEN, sm.RESPOND, sm.RESPONDENT).to == sm.OBS_RESPONDED
    assert sm.resolve_observation(sm.OBS_RESPONDED, sm.CLOSE, roles.AUDITOR_ACTOR).to \
        == sm.OBS_CLOSED
    assert sm.resolve_observation(sm.OBS_RESPONDED, sm.RETURN, roles.AUDITOR_ACTOR).to \
        == sm.OBS_OPEN
    with pytest.raises(sm.InvalidTransition):       # IAA-BR-302: no closure before a response
        sm.resolve_observation(sm.OBS_OPEN, sm.CLOSE, roles.AUDITOR_ACTOR)
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve_observation(sm.OBS_RESPONDED, sm.CLOSE, roles.FINANCE_ACTOR)
    with pytest.raises(sm.InvalidTransition):       # closed is final
        sm.resolve_observation(sm.OBS_CLOSED, sm.RETURN, roles.AUDITOR_ACTOR)


# ── roles ───────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role,kind", [
    (roles.FINANCE, roles.FINANCE_ACTOR), (roles.AUDITOR, roles.AUDITOR_ACTOR),
    (roles.SYSTEM_ADMIN, roles.ADMIN_ACTOR), (roles.HOD, roles.APPROVER_ACTOR),
    (roles.DEAN, roles.APPROVER_ACTOR), (roles.DIRECTOR, roles.APPROVER_ACTOR),
    ("faculty", roles.OWNER), ("staff", roles.OWNER), (None, roles.OWNER)])
def test_an_acting_role_maps_to_one_kind_of_actor(role, kind):
    assert roles.actor_kind(role) == kind


def test_hod_is_department_scoped_but_dean_and_director_are_not():
    assert {roles.HOD} == roles.DEPARTMENT_SCOPED
    assert {DEAN, DIRECTOR} <= roles.APPROVERS


# ── policy ──────────────────────────────────────────────────────────────────────────────

def _policy(**over):
    return policy_rules.parse({**POLICY, **over})


def _errors(**over) -> list[dict]:
    with pytest.raises(policy_rules.PolicyInvalid) as exc:
        policy_rules.parse({**POLICY, **over})
    return exc.value.errors


def test_the_reference_policy_is_valid():
    p = _policy()
    assert p.approval_timeout_hours == 48
    assert p.ta_high_value_threshold == Decimal("25000")
    assert len(p.routes) == 3 and p.request_types == ("voucher", "reimbursement")


def _error_fields(**over) -> set[str]:
    return {e["field"] for e in _errors(**over)}


def test_a_route_must_be_an_object_with_a_known_kind_and_real_approving_roles():
    good = POLICY["routes"][0]
    assert "routes[0]" in _error_fields(routes=["not an object"])
    assert "routes[0].kind" in _error_fields(routes=[{**good, "kind": "loan"}])
    assert "routes[0].levels" in _error_fields(routes=[{**good, "levels": []}])
    assert "routes[0].levels" in _error_fields(routes=[{**good, "levels": "iaa_hod"}])
    assert "routes[0].levels" in _error_fields(routes=[{**good, "levels": ["iaa_finance_staff"]}])


def test_request_types_must_be_a_list_of_names():
    assert "request_types" in _error_fields(request_types="voucher")
    assert "request_types" in _error_fields(request_types=["voucher", " "])
    assert "request_types" in _error_fields(request_types=[])


@pytest.mark.parametrize("required", [{"expense": -1, "ta": 1}, {"expense": "many", "ta": 1},
                                      "one"])
def test_required_documents_must_be_whole_numbers_of_zero_or_more(required):
    assert any(f.startswith("required_documents") for f in _error_fields(required_documents=required))


@pytest.mark.parametrize("hours", [0, -3, "x", None])
def test_the_timeout_must_be_whole_hours_above_zero(hours):
    assert any(e["field"] == "approval_timeout_hours"
               for e in _errors(approval_timeout_hours=hours))


def test_a_policy_needs_request_types_and_a_route_for_each_kind():
    assert any(e["field"] == "request_types" for e in _errors(request_types=[]))
    only_expense = [r for r in POLICY["routes"] if r["kind"] == "expense"]
    assert any("ta route" in e["message"] for e in _errors(routes=only_expense))


def test_only_authority_roles_can_approve_or_receive_escalations():
    bad_level = [{"kind": "expense", "levels": [roles.FINANCE], "escalation_designation": DEAN},
                 *[r for r in POLICY["routes"] if r["kind"] == "ta"]]
    assert any(e["field"] == "routes[0].levels" for e in _errors(routes=bad_level))
    bad_escalation = [{"kind": "expense", "levels": [HOD], "escalation_designation": "x"},
                      *[r for r in POLICY["routes"] if r["kind"] == "ta"]]
    assert any(e["field"] == "routes[0].escalation_designation"
               for e in _errors(routes=bad_escalation))


def test_a_role_may_appear_once_on_a_route():
    dup = [{"kind": "expense", "levels": [HOD, HOD], "escalation_designation": ""},
           *[r for r in POLICY["routes"] if r["kind"] == "ta"]]
    assert any("only once" in e["message"] for e in _errors(routes=dup))


def test_overlapping_routes_for_the_same_scope_are_refused():
    clash = [*POLICY["routes"], {"kind": "expense", "min_amount": "40000", "max_amount": "60000",
                                 "levels": [DEAN], "escalation_designation": ""}]
    assert any("overlap" in e["message"] for e in _errors(routes=clash))


def test_a_route_band_must_be_ordered_and_numeric():
    backwards = [{"kind": "expense", "min_amount": "100", "max_amount": "50",
                  "levels": [HOD]}, *[r for r in POLICY["routes"] if r["kind"] == "ta"]]
    assert any(e["field"] == "routes[0].max_amount" for e in _errors(routes=backwards))
    junk = [{"kind": "expense", "min_amount": "abc", "levels": [HOD]},
            *[r for r in POLICY["routes"] if r["kind"] == "ta"]]
    assert any(e["field"] == "routes[0].min_amount" for e in _errors(routes=junk))


def test_every_anomaly_category_needs_resolvers_who_can_resolve():
    assert any(e["field"] == "anomaly_resolvers.budget" for e in _errors(
        anomaly_resolvers={**POLICY["anomaly_resolvers"], "budget": []}))
    assert any(e["field"] == "anomaly_resolvers.policy" for e in _errors(
        anomaly_resolvers={**POLICY["anomaly_resolvers"], "policy": ["iaa_system_admin"]}))


def test_required_documents_and_threshold_cannot_be_negative():
    assert any(e["field"] == "required_documents.ta"
               for e in _errors(required_documents={"expense": 1, "ta": -1}))
    assert any(e["field"] == "ta_high_value_threshold"
               for e in _errors(ta_high_value_threshold="-5"))


def test_route_selection_honours_each_side_of_an_amount_threshold():
    p = _policy()
    below = policy_rules.select_route(p, sm.EXPENSE, "voucher", "CSE", Decimal("49999.99"))
    at = policy_rules.select_route(p, sm.EXPENSE, "voucher", "CSE", Decimal("50000"))
    assert below.levels == (HOD,) and at.levels == (HOD, DEAN)


def test_the_most_specific_route_wins_and_a_gap_is_reported():
    specific = {"kind": "expense", "department": "CSE", "request_type": "voucher",
                "min_amount": "0", "max_amount": "50000", "levels": [DEAN],
                "escalation_designation": DIRECTOR}
    p = _policy(routes=[*[r for r in POLICY["routes"] if r["kind"] == "ta"], specific,
                        {"kind": "expense", "min_amount": "0", "max_amount": "50000",
                         "levels": [HOD]}])
    assert policy_rules.select_route(p, sm.EXPENSE, "voucher", "CSE", Decimal(5)).levels \
        == (DEAN,)
    assert policy_rules.select_route(p, sm.EXPENSE, "voucher", "ECE", Decimal(5)).levels \
        == (HOD,)
    with pytest.raises(policy_rules.NoRoute):
        policy_rules.select_route(p, sm.EXPENSE, "voucher", "CSE", Decimal("90000"))


def test_a_ta_claim_is_high_value_at_the_threshold_and_above():
    p = _policy()
    assert not policy_rules.is_high_value(p, Decimal("24999.99"))
    assert policy_rules.is_high_value(p, Decimal("25000"))


# ── routing ─────────────────────────────────────────────────────────────────────────────

def test_the_next_authority_is_the_next_level_then_the_escalation_role_then_nobody():
    levels = (HOD, DEAN)
    assert routing.next_authority(levels, 0, DIRECTOR) == routing.Target(1, DEAN)
    assert routing.next_authority(levels, 1, DIRECTOR) == routing.Target(2, DIRECTOR)
    assert routing.next_authority(levels, 1, "") is None
    assert routing.next_authority(levels, 2, DIRECTOR) is None     # already escalated


def test_the_final_level_is_the_last_configured_one_or_beyond():
    assert not routing.is_final_level((HOD, DEAN), 0)
    assert routing.is_final_level((HOD, DEAN), 1)
    assert routing.is_final_level((HOD,), 1)           # an escalation level decides finally


# ── submission validation (IAA-BR-101) ──────────────────────────────────────────────────

def _sub(**over):
    base = {"kind": sm.EXPENSE, "title": "Kits", "department": "CSE", "request_type": "voucher",
            "amount": Decimal("100"), "description": "Soldering", "purpose": "",
            "trip_start": None, "trip_end": None, "documents": 1}
    return Submission(**{**base, **over})


def _fields(sub, docs=1):
    return {e["field"] for e in submission_errors(sub, ("voucher",), docs)}


def test_a_complete_expense_has_no_errors():
    assert submission_errors(_sub(), ("voucher",), 1) == []


def test_an_empty_expense_names_every_missing_field():
    empty = _sub(title="", department="", request_type="", amount=None, description="",
                 documents=0)
    assert _fields(empty) == {"title", "department", "request_type", "amount", "description",
                              "documents"}


def test_the_amount_must_be_above_zero_and_the_type_must_be_configured():
    assert "amount" in _fields(_sub(amount=Decimal("0")))
    assert "request_type" in _fields(_sub(request_type="gift"))


def test_a_ta_claim_needs_a_purpose_and_a_sensible_trip():
    ta = {"kind": sm.TA, "title": "", "description": "", "request_type": "",
          "purpose": "Conference", "trip_start": date(2026, 5, 1), "trip_end": date(2026, 5, 3)}
    assert submission_errors(_sub(**ta), ("voucher",), 1) == []
    assert "purpose" in _fields(_sub(**{**ta, "purpose": ""}))
    assert "trip_start" in _fields(_sub(**{**ta, "trip_start": None}))
    assert "trip_end" in _fields(_sub(**{**ta, "trip_end": date(2026, 4, 1)}))


def test_the_required_document_count_is_enforced():
    assert "documents" in _fields(_sub(documents=1), docs=2)
    assert "documents" not in _fields(_sub(documents=2), docs=2)


# ── budget (IAA-BR-102) ─────────────────────────────────────────────────────────────────

def test_available_budget_is_the_sum_of_the_ledger_and_zero_when_empty():
    assert budget.available([Decimal("500000"), Decimal("-12000"), Decimal("1000")]) \
        == Decimal("489000")
    assert budget.available([]) == Decimal("0")


def test_a_shortfall_is_never_negative():
    assert budget.shortfall(Decimal("700"), Decimal("500")) == Decimal("200")
    assert budget.shortfall(Decimal("500"), Decimal("700")) == Decimal("0")
