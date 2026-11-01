"""Unit tests for CMS state machine transitions (BW-CMS-01..08, CW-CMS-01..03)."""
import pytest
from modules.complaints.domain.entities import ComplaintStatus, TERMINAL_STATUSES
from modules.complaints.domain.errors import InvalidTransition, RuleViolation
from modules.complaints.domain.state_machine import LEGAL_TRANSITIONS, validate_transition


def test_transition_matrix_properties():
    """Verify state machine invariants."""
    # Terminal states should have no outgoing transitions except Closed reopening
    for trans in LEGAL_TRANSITIONS:
        if trans.frm == ComplaintStatus.REJECTED:
            pytest.fail("Rejected state should not have outgoing transitions.")


def test_bw_cms_01_intake_to_resolved():
    """BW-CMS-01: Submitted -> In Progress -> Resolved."""
    t1 = validate_transition(ComplaintStatus.SUBMITTED, ComplaintStatus.IN_PROGRESS, permissions={"*"})
    assert t1.to == ComplaintStatus.IN_PROGRESS

    t2 = validate_transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.RESOLVED,
        permissions={"*"},
        resolution_details="Issue resolved",
    )
    assert t2.to == ComplaintStatus.RESOLVED


def test_bw_cms_02_and_03_closure_verification():
    """BW-CMS-02 & 03: Resolved -> Closed upon verification."""
    t = validate_transition(ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, permissions={"*"})
    assert t.to == ComplaintStatus.CLOSED


def test_bw_cms_04_intake_to_rejection():
    """BW-CMS-04: Submitted / In Progress -> Rejected."""
    t1 = validate_transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.REJECTED,
        permissions={"*"},
        rejection_reason="Duplicate complaint",
    )
    assert t1.to == ComplaintStatus.REJECTED

    t2 = validate_transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.REJECTED,
        permissions={"*"},
        rejection_reason="Out of scope",
    )
    assert t2.to == ComplaintStatus.REJECTED


def test_bw_cms_06_reopening_approved():
    """BW-CMS-06: Closed -> In Progress."""
    t = validate_transition(ComplaintStatus.CLOSED, ComplaintStatus.IN_PROGRESS, permissions={"*"})
    assert t.to == ComplaintStatus.IN_PROGRESS

