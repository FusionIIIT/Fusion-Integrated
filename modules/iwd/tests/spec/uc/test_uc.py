"""Specification tests for Use Cases (UC)."""
from modules.iwd.domain.state_machine import transition


class TestUseCases:
    """Covers UC-IWD test obligations."""

    def test_uc_iwd_001_submit_maintenance_complaint_lifecycle(self):
        """TEST-UC-001 / UC-IWD-001 Main Flow: Lifecycle progression."""
        t1 = transition("submitted", "assign_engineer", "system")
        assert t1.allowed is True
        assert t1.next_state == "assigned"
