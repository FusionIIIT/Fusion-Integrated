"""Specification tests for Workflows (WF)."""
from modules.iwd.domain.state_machine import transition


class TestWorkflows:
    """Covers WF-IWD test obligations."""

    def test_bw_iwd_01_intake_and_assessment_workflow(self):
        """TEST-WF-001 / BW-IWD-01: Complaint Intake and Assessment Workflow."""
        state = "submitted"

        t1 = transition(state, "assign_engineer", "system")
        assert t1.allowed
        state = t1.next_state
        assert state == "assigned"

        t2 = transition(state, "record_assessment", "engineer")
        assert t2.allowed
        state = t2.next_state
        assert state == "assessed"
