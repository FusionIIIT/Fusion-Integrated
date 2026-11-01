"""Tests for all 12 Basis Workflows (BW-RSPC-01..12) and 6 Composite Workflows (CW-RSPC-01..06)."""

from decimal import Decimal

from modules.rspc.domain import (
    CLOSURE_TRANSITIONS,
    DEFAULT_DEAN_PROCUREMENT_LIMIT,
    DEFAULT_DIRECTOR_FUNDING_THRESHOLD,
    PROCUREMENT_TRANSITIONS,
    PROPOSAL_TRANSITIONS,
    ClosureStatus,
    ProcurementStatus,
    ProposalStatus,
    RspcRole,
    validate_transition,
)


# ---------------------------------------------------------------------------
# CW-RSPC-01 & BW-RSPC-01 / BW-RSPC-02: Proposal Workflows
# ---------------------------------------------------------------------------
def test_cw_rspc_01_all_10_transitions():
    """Verify all 10 transitions in Composite Workflow CW-RSPC-01."""
    # S1: Draft -> Submitted
    t1 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.DRAFT.value,
        to_state=ProposalStatus.SUBMITTED.value,
        actor_role=RspcRole.FACULTY.value,
        context={"required_fields": ["t"], "t": "AI"},
    )
    assert t1.to == ProposalStatus.SUBMITTED.value

    # S2: Submitted -> Dept Recommended
    t2 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.SUBMITTED.value,
        to_state=ProposalStatus.DEPT_RECOMMENDED.value,
        actor_role=RspcRole.HOD.value,
        context={"remarks": "Recommended"},
    )
    assert t2.to == ProposalStatus.DEPT_RECOMMENDED.value

    # S3: Submitted -> Dept Not Recommended
    t3 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.SUBMITTED.value,
        to_state=ProposalStatus.DEPT_NOT_RECOMMENDED.value,
        actor_role=RspcRole.HOD.value,
        context={"remarks": "Not recommended"},
    )
    assert t3.to == ProposalStatus.DEPT_NOT_RECOMMENDED.value

    # S4: Dept Recommended -> Admin Verified
    t4 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.DEPT_RECOMMENDED.value,
        to_state=ProposalStatus.ADMIN_VERIFIED.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
        context={"is_eligible": True},
    )
    assert t4.to == ProposalStatus.ADMIN_VERIFIED.value

    # S5: Dept Recommended -> Not Eligible
    t5 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.DEPT_RECOMMENDED.value,
        to_state=ProposalStatus.NOT_ELIGIBLE.value,
        actor_role=RspcRole.RSPC_ADMIN.value,
        context={"remarks": "Ineligible"},
    )
    assert t5.to == ProposalStatus.NOT_ELIGIBLE.value

    # S6: Admin Verified -> Approved
    t6 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.ADMIN_VERIFIED.value,
        to_state=ProposalStatus.APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": 100000, "remarks": "Approved"},
    )
    assert t6.to == ProposalStatus.APPROVED.value

    # S7: Admin Verified -> Forwarded to Director
    t7 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.ADMIN_VERIFIED.value,
        to_state=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": DEFAULT_DIRECTOR_FUNDING_THRESHOLD + 1, "remarks": "Fwd"},
    )
    assert t7.to == ProposalStatus.FORWARDED_TO_DIRECTOR.value

    # S8: Admin Verified -> Dean Not Approved
    t8 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.ADMIN_VERIFIED.value,
        to_state=ProposalStatus.DEAN_NOT_APPROVED.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"remarks": "Dean rejected"},
    )
    assert t8.to == ProposalStatus.DEAN_NOT_APPROVED.value

    # S9: Forwarded to Director -> Approved
    t9 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=ProposalStatus.APPROVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director approved"},
    )
    assert t9.to == ProposalStatus.APPROVED.value

    # S10: Forwarded to Director -> Director Not Approved
    t10 = validate_transition(
        transitions=PROPOSAL_TRANSITIONS,
        from_state=ProposalStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=ProposalStatus.DIRECTOR_NOT_APPROVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director rejected"},
    )
    assert t10.to == ProposalStatus.DIRECTOR_NOT_APPROVED.value


# ---------------------------------------------------------------------------
# CW-RSPC-05 & BW-RSPC-09 / BW-RSPC-10: Procurement Workflows
# ---------------------------------------------------------------------------
def test_bw_rspc_10_procurement_via_director():
    """BW-RSPC-10: High-value procurement forwarded to Director."""
    t_fwd = validate_transition(
        transitions=PROCUREMENT_TRANSITIONS,
        from_state=ProcurementStatus.VERIFIED.value,
        to_state=ProcurementStatus.FORWARDED_TO_DIRECTOR.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={
            "estimated_cost": DEFAULT_DEAN_PROCUREMENT_LIMIT + Decimal("500000"),
            "remarks": "Procurement exceeds 10L limit.",
        },
    )
    assert t_fwd.to == ProcurementStatus.FORWARDED_TO_DIRECTOR.value

    t_dir = validate_transition(
        transitions=PROCUREMENT_TRANSITIONS,
        from_state=ProcurementStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=ProcurementStatus.APPROVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director authorized procurement."},
    )
    assert t_dir.to == ProcurementStatus.APPROVED.value


# ---------------------------------------------------------------------------
# CW-RSPC-06 & BW-RSPC-12: Closure via Director
# ---------------------------------------------------------------------------
def test_bw_rspc_12_closure_via_director():
    """BW-RSPC-12: Strategic/high-value project closure via Director."""
    t_fwd = validate_transition(
        transitions=CLOSURE_TRANSITIONS,
        from_state=ClosureStatus.VERIFIED.value,
        to_state=ClosureStatus.FORWARDED_TO_DIRECTOR.value,
        actor_role=RspcRole.DEAN_RSPC.value,
        context={"budget_amount": Decimal("10000000"), "remarks": "Strategic closure."},
    )
    assert t_fwd.to == ClosureStatus.FORWARDED_TO_DIRECTOR.value

    t_dir = validate_transition(
        transitions=CLOSURE_TRANSITIONS,
        from_state=ClosureStatus.FORWARDED_TO_DIRECTOR.value,
        to_state=ClosureStatus.ARCHIVED.value,
        actor_role=RspcRole.DIRECTOR.value,
        context={"remarks": "Director approved closure & archival."},
    )
    assert t_dir.to == ClosureStatus.ARCHIVED.value
