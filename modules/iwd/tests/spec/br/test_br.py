"""Specification tests for Business Rules (BR)."""
from decimal import Decimal

from modules.iwd.domain.routing import classify_cost_band
from modules.iwd.domain.state_machine import transition


class TestBusinessRules:
    """Covers BR-IWD test obligations."""

    def test_br_iwd_003_cost_band_routing(self):
        """TEST-BR-003 / BR-IWD-003: Cost-band routing rules."""
        assert classify_cost_band(Decimal("0")).band == "low"
        assert classify_cost_band(Decimal("24999")).band == "low"
        assert classify_cost_band(Decimal("25000")).band == "mid"
        assert classify_cost_band(Decimal("250000")).band == "mid"
        assert classify_cost_band(Decimal("250001")).band == "high"

    def test_br_iwd_009_state_machine_transition(self):
        """TEST-BR-009 / BR-IWD-009: Transitions enforce lifecycle progression."""
        res_valid = transition("submitted", "assign_engineer", "system")
        assert res_valid.allowed is True
        assert res_valid.next_state == "assigned"

        res_invalid = transition("submitted", "approve_low_cost", "iwd_admin")
        assert res_invalid.allowed is False
