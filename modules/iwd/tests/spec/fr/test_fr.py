"""Specification tests for Functional Requirements (FR)."""
from decimal import Decimal

from modules.iwd.domain.assignment import EngineerCandidate, select_best_engineer
from modules.iwd.domain.routing import classify_cost_band


class TestFunctionalRequirements:
    """Covers AFR-IWD test obligations."""

    def test_afr_iwd_007_workload_routing(self):
        """TEST-FR-007 / AFR-IWD-007: Automatic workload routing."""
        candidates = [
            EngineerCandidate(engineer_id=101, discipline="civil", active_load=4),
            EngineerCandidate(engineer_id=102, discipline="civil", active_load=1),
        ]
        best_id = select_best_engineer("civil", candidates)
        assert best_id == 102

    def test_afr_iwd_014_cost_band_classification(self):
        """TEST-FR-014 / AFR-IWD-014: Cost band thresholding."""
        assert classify_cost_band(Decimal("15000")).band == "low"
        assert classify_cost_band(Decimal("100000")).band == "mid"
        assert classify_cost_band(Decimal("1000000")).band == "high"
