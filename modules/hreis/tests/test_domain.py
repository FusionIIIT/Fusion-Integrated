"""Exhaustive pure-domain tests for the live HR-EIS workflows."""

from decimal import Decimal

import pytest

from modules.hreis.domain import leave
from modules.hreis.domain import workflow as wf


@pytest.mark.parametrize(
    "family,count",
    [
        (wf.LEAVE, 4),
        (wf.APPRAISAL, 6),
        (wf.LTC, 6),
        (wf.CPDA, 6),
    ],
)
def test_all_declared_workflow_edges_are_unique_and_present(family, count):
    # HR-CFR-003, HR-AFR-070, CW-HR-01, CW-HR-02, CW-HR-03, CW-HR-04: frozen spec edges exist.
    edges = [t for t in wf.TRANSITIONS if t.family == family]
    assert len(edges) == count
    assert len({(t.source, t.event) for t in edges}) == count
    assert all(t.specification for t in edges)


@pytest.mark.parametrize("edge", wf.TRANSITIONS)
def test_every_spec_edge_accepts_its_actor_with_all_guards(edge):
    # HR-AFR-074, BR-HR-009: actor and guards are required per transition.
    conditions = dict.fromkeys(edge.guards, True)
    assert (
        wf.resolve(edge.family, edge.source, edge.event, edge.actor, guard_results=conditions)
        == edge
    )
    assert edge.event in wf.allowed_events(edge.family, edge.source, edge.actor)


@pytest.mark.parametrize("edge", wf.TRANSITIONS)
def test_every_spec_edge_rejects_a_wrong_actor(edge):
    with pytest.raises(wf.ActorNotAllowed):
        wf.resolve(
            edge.family,
            edge.source,
            edge.event,
            "unrelated_role",
            guard_results=dict.fromkeys(edge.guards, True),
        )


@pytest.mark.parametrize("edge", wf.TRANSITIONS)
def test_each_required_guard_is_fail_closed(edge):
    # HR-AFR-075, HR-AFR-076, HR-AFR-106, BR-HR-023, BR-HR-030: missing guards cannot be bypassed.
    for missing_guard in edge.guards:
        conditions = {guard: True for guard in edge.guards if guard != missing_guard}
        with pytest.raises(wf.GuardFailed) as exc:
            wf.resolve(edge.family, edge.source, edge.event, edge.actor, guard_results=conditions)
        assert exc.value.guard == missing_guard
        conditions[missing_guard] = False
        with pytest.raises(wf.GuardFailed):
            wf.resolve(edge.family, edge.source, edge.event, edge.actor, guard_results=conditions)


@pytest.mark.parametrize("family,terminal_states", wf.TERMINAL_STATES.items())
def test_terminal_states_cannot_move(family, terminal_states):
    # HR-AFR-071, HR-AFR-072, BR-HR-023: final outcomes cannot be mutated.
    for state in terminal_states:
        assert wf.is_terminal(family, state)
        for actor in (wf.EMPLOYEE, wf.HR_ADMINISTRATOR, wf.AUTHORITY, wf.ACCOUNTANT):
            assert not wf.allowed_events(family, state, actor)
        with pytest.raises(wf.InvalidTransition):
            wf.resolve(family, state, "submit", wf.EMPLOYEE, guard_results={})


def test_claim_approval_is_not_the_same_as_financial_processing():
    for family in (wf.LTC, wf.CPDA):
        assert not wf.is_terminal(family, wf.APPROVED)
        edge = next(
            t
            for t in wf.TRANSITIONS
            if t.family == family and t.event == "record_financial_processing"
        )
        assert edge.actor == wf.ACCOUNTANT
        assert "financial_correctness_verified" in edge.guards
        assert edge.target == wf.FINANCIAL_PROCESSING_RECORDED
        assert wf.is_terminal(family, edge.target)


def test_forward_moves_the_route_not_the_request_to_a_new_terminal_state():
    # HR-AFR-073, HR-AFR-075, BR-HR-023: forwarding advances only the route step.
    for family in (wf.LEAVE, wf.LTC, wf.CPDA):
        edge = next(t for t in wf.TRANSITIONS if t.family == family and t.event == "forward")
        assert edge.source == edge.target == wf.PENDING_AUTHORITY
        assert edge.effect == "advance_route_step"
        assert "next_authority_exists" in edge.guards


def test_no_unspecified_return_or_appraisal_rejection_edge():
    for family in wf.FAMILIES:
        assert all(t.event != "return" for t in wf.TRANSITIONS if t.family == family)
    assert not any(t.event == "reject" for t in wf.TRANSITIONS if t.family == wf.APPRAISAL)
    with pytest.raises(wf.InvalidTransition):
        wf.resolve(wf.LTC, wf.APPROVED, "return", wf.ACCOUNTANT, guard_results={})


def test_unknown_family_and_unsupported_transition_denied():
    with pytest.raises(wf.UnknownWorkflow):
        wf.resolve("payroll", wf.DRAFT, "submit", wf.EMPLOYEE, guard_results={})
    with pytest.raises(wf.InvalidTransition):
        wf.resolve(wf.LEAVE, wf.DRAFT, "approve", wf.AUTHORITY, guard_results={})


def _leave(**overrides):
    params = {
        "leave_type": "Casual",
        "duration": Decimal("1.5"),
        "justification": "Medical appointment",
        "available_balance": Decimal("4"),
        "is_eligible": True,
    }
    params.update(overrides)
    return leave.validate_submission(**params)


@pytest.mark.parametrize("leave_type", sorted(leave.LEAVE_TYPES))
def test_supported_six_leave_types(leave_type):
    # HR-AFR-030, HR-AFR-031, HR-AFR-032, HR-AFR-033, HR-AFR-034, HR-AFR-035, BR-HR-007, BR-HR-034.
    assert _leave(leave_type=leave_type).leave_type == leave_type
    assert len(leave.LEAVE_TYPES) == 6


@pytest.mark.parametrize("leave_type", ["Compensatory", "Sick", "", None])
def test_undocumented_leave_type_denied(leave_type):
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        _leave(leave_type=leave_type)
    assert exc.value.code == "unsupported_leave_type"


@pytest.mark.parametrize(
    "duration",
    [
        Decimal("0"),
        Decimal("-2"),
        Decimal("NaN"),
        Decimal("Infinity"),
        1.0,
        "1",
    ],
)
def test_invalid_duration_rejected(duration):
    # HR-AFR-037, BR-HR-007: reject absent, malformed and nonpositive duration.
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        _leave(duration=duration)
    assert exc.value.code == "invalid_duration"


@pytest.mark.parametrize("justification", ["", "   ", None])
def test_justification_required(justification):
    # HR-AFR-038, BR-HR-007: no leave without justification.
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        _leave(justification=justification)
    assert exc.value.code == "missing_justification"


@pytest.mark.parametrize(
    "balance,eligible",
    [
        (None, True),
        (Decimal("3"), None),
        (None, None),
    ],
)
def test_unconfigured_leave_policy_fails_closed(balance, eligible):
    # HR-AFR-039, HR-AFR-040, BR-HR-008: eligibility/balance must be configured.
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        _leave(available_balance=balance, is_eligible=eligible)
    assert exc.value.code == "policy_unavailable"


def test_ineligibility_and_insufficient_balance_both_block_submission():
    # HR-AFR-039, HR-AFR-040, BR-HR-008: enforce both prerequisites, not just one.
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        _leave(is_eligible=False)
    assert exc.value.code == "ineligible"
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        _leave(available_balance=Decimal("1.49"))
    assert exc.value.code == "insufficient_balance"
    assert _leave(available_balance=Decimal("1.50")).duration == Decimal("1.5")


def test_decimal_ledger_balance_and_reversal_are_exact():
    # HR-AFR-042, HR-AFR-043, BR-HR-010: immutable debit/credit arithmetic is exact.
    assert leave.ledger_balance(
        [
            Decimal("12"),
            Decimal("-1.2"),
            Decimal("-0.1"),
            Decimal("0.1"),
        ]
    ) == Decimal("10.8")


@pytest.mark.parametrize("entry", [0.2, Decimal("NaN"), Decimal("Infinity")])
def test_ledger_rejects_non_exact_or_non_finite_entries(entry):
    with pytest.raises(leave.InvalidLeaveRequest) as exc:
        leave.ledger_balance([Decimal("5"), entry])
    assert exc.value.code == "invalid_entry"
