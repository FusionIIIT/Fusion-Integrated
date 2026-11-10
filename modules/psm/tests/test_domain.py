"""
Pure Python Unit Tests for PSM Domain Layer.
Runs fast in-memory without any database connections or Django dependencies.
"""

import unittest
from decimal import Decimal

from modules.psm.domain.indent_state import (
    IndentState,
    can_transition,
    is_modifiable,
    TRANSITION_MATRIX,
)
from modules.psm.domain.rules import (
    validate_indent_completeness,
    is_possible_duplicate,
    determine_procurement_routing,
    determine_procurement_method,
    validate_rejection_justification,
)
from modules.psm.domain.three_way_match import perform_three_way_match


class TestIndentStateTransitions(unittest.TestCase):
    """Test BW-PSM-01, BW-PSM-02, BW-PSM-03, BW-PSM-07, CW-PSM-01 transitions."""

    def test_draft_transitions(self):
        self.assertTrue(can_transition(IndentState.DRAFT, IndentState.SUBMITTED))
        self.assertTrue(can_transition(IndentState.DRAFT, IndentState.WITHDRAWN))
        self.assertFalse(can_transition(IndentState.DRAFT, IndentState.APPROVED))
        self.assertFalse(can_transition("DRAFT", "STOCK_CHECKED"))

    def test_submitted_transitions(self):
        self.assertTrue(can_transition(IndentState.SUBMITTED, IndentState.STOCK_CHECKED))
        self.assertTrue(can_transition(IndentState.SUBMITTED, IndentState.REJECTED))
        self.assertTrue(can_transition(IndentState.SUBMITTED, IndentState.WITHDRAWN))
        self.assertFalse(can_transition(IndentState.SUBMITTED, IndentState.APPROVED))

    def test_stock_checked_transitions(self):
        self.assertTrue(can_transition(IndentState.STOCK_CHECKED, IndentState.DEPT_REVIEWED))
        self.assertTrue(can_transition(IndentState.STOCK_CHECKED, IndentState.REJECTED))
        self.assertTrue(can_transition(IndentState.STOCK_CHECKED, IndentState.WITHDRAWN))

    def test_dept_reviewed_transitions(self):
        self.assertTrue(can_transition(IndentState.DEPT_REVIEWED, IndentState.HEAD_RECOMMENDED))
        self.assertTrue(can_transition(IndentState.DEPT_REVIEWED, IndentState.REJECTED))

    def test_head_recommended_transitions(self):
        self.assertTrue(can_transition(IndentState.HEAD_RECOMMENDED, IndentState.AWAITING_FINAL_APPROVAL))
        self.assertTrue(can_transition(IndentState.HEAD_RECOMMENDED, IndentState.REJECTED))

    def test_final_approval_transitions(self):
        self.assertTrue(can_transition(IndentState.AWAITING_FINAL_APPROVAL, IndentState.APPROVED))
        self.assertTrue(can_transition(IndentState.AWAITING_FINAL_APPROVAL, IndentState.REJECTED))

    def test_terminal_states(self):
        for term in [IndentState.APPROVED, IndentState.REJECTED, IndentState.WITHDRAWN]:
            self.assertFalse(can_transition(term, IndentState.DRAFT))
            self.assertFalse(can_transition(term, IndentState.SUBMITTED))
            self.assertEqual(len(TRANSITION_MATRIX[term.value]), 0)

    def test_is_modifiable_enforcement(self):
        """BR-PSM-007: Modifiable only in DRAFT and SUBMITTED states."""
        self.assertTrue(is_modifiable(IndentState.DRAFT))
        self.assertTrue(is_modifiable("DRAFT"))
        self.assertTrue(is_modifiable(IndentState.SUBMITTED))
        self.assertTrue(is_modifiable("SUBMITTED"))
        self.assertFalse(is_modifiable(IndentState.STOCK_CHECKED))
        self.assertFalse(is_modifiable(IndentState.DEPT_REVIEWED))
        self.assertFalse(is_modifiable(IndentState.HEAD_RECOMMENDED))
        self.assertFalse(is_modifiable(IndentState.AWAITING_FINAL_APPROVAL))
        self.assertFalse(is_modifiable(IndentState.APPROVED))
        self.assertFalse(is_modifiable(IndentState.REJECTED))
        self.assertFalse(is_modifiable(IndentState.WITHDRAWN))


class TestDomainRules(unittest.TestCase):
    """Test validation, duplicate checks, routing rules, and justifications."""

    def test_validate_indent_completeness_valid(self):
        data = {
            "item_details": "4K 27-inch IPS Monitors",
            "quantity": 10,
            "estimated_cost": Decimal("250000.00"),
            "justification": "Required for newly established AI/ML research lab.",
        }
        # Should not raise
        validate_indent_completeness(data)

    def test_validate_indent_completeness_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_indent_completeness({
                "item_details": "Monitors",
                "quantity": 10,
            })

    def test_validate_indent_completeness_invalid_quantity(self):
        with self.assertRaises(ValueError):
            validate_indent_completeness({
                "item_details": "Monitors",
                "quantity": 0,
                "estimated_cost": 1000,
                "justification": "Need it",
            })

    def test_validate_indent_completeness_invalid_cost(self):
        with self.assertRaises(ValueError):
            validate_indent_completeness({
                "item_details": "Monitors",
                "quantity": 5,
                "estimated_cost": -50,
                "justification": "Need it",
            })

    def test_is_possible_duplicate_detected(self):
        existing = [
            {
                "indent_id": "IND-2026-001",
                "item_details": "Ergonomic Chairs",
                "estimated_cost": 50000.0,
                "status": "SUBMITTED",
            }
        ]
        new_indent = {
            "item_details": "Ergonomic Chairs",
            "estimated_cost": 51000.0,  # within 5%
        }
        self.assertTrue(is_possible_duplicate(new_indent, existing))

    def test_is_possible_duplicate_different_cost(self):
        existing = [
            {
                "indent_id": "IND-2026-001",
                "item_details": "Ergonomic Chairs",
                "estimated_cost": 50000.0,
                "status": "SUBMITTED",
            }
        ]
        new_indent = {
            "item_details": "Ergonomic Chairs",
            "estimated_cost": 80000.0,  # 60% difference
        }
        self.assertFalse(is_possible_duplicate(new_indent, existing))

    def test_is_possible_duplicate_inactive_existing_ignored(self):
        existing = [
            {
                "indent_id": "IND-2026-001",
                "item_details": "Ergonomic Chairs",
                "estimated_cost": 50000.0,
                "status": "APPROVED",  # Terminal state
            }
        ]
        new_indent = {
            "item_details": "Ergonomic Chairs",
            "estimated_cost": 50000.0,
        }
        self.assertFalse(is_possible_duplicate(new_indent, existing))

    def test_determine_procurement_routing(self):
        """BR-PSM-003: Internal issue if stock available, else external procurement."""
        self.assertEqual(determine_procurement_routing(requested_qty=5, available_stock=10), "INTERNAL_ISSUE")
        self.assertEqual(determine_procurement_routing(requested_qty=10, available_stock=10), "INTERNAL_ISSUE")
        self.assertEqual(determine_procurement_routing(requested_qty=15, available_stock=10), "EXTERNAL_PROCUREMENT")
        self.assertEqual(determine_procurement_routing(requested_qty=5, available_stock=0), "EXTERNAL_PROCUREMENT")

    def test_determine_procurement_method(self):
        """BR-PSM-008: Direct vs Tender threshold."""
        self.assertEqual(determine_procurement_method(50000, tender_threshold=100000), "DIRECT")
        self.assertEqual(determine_procurement_method(100000, tender_threshold=100000), "TENDER")
        self.assertEqual(determine_procurement_method(150000, tender_threshold=100000), "TENDER")

    def test_validate_rejection_justification(self):
        """BR-PSM-005: Rejection mandates non-empty justification."""
        # Non-reject decisions don't require justification
        validate_rejection_justification("APPROVE", "")
        # Reject with valid justification succeeds
        validate_rejection_justification("REJECT", "Exceeds annual department budget limits.")
        # Reject without justification fails
        with self.assertRaises(ValueError):
            validate_rejection_justification("REJECT", "")
        with self.assertRaises(ValueError):
            validate_rejection_justification("REJECTED", "   ")


class TestThreeWayMatch(unittest.TestCase):
    """Test BR-PSM-017, BR-PSM-018: 3-Way Match Verification."""

    def test_perfect_match(self):
        result = perform_three_way_match(
            po_amount=100000.0,
            grn_accepted_qty=100,
            unit_price=1000.0,
            invoice_amount=100000.0,
        )
        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["is_matched"])
        self.assertEqual(len(result["discrepancies"]), 0)

    def test_invoice_mismatch(self):
        result = perform_three_way_match(
            po_amount=100000.0,
            grn_accepted_qty=100,
            unit_price=1000.0,
            invoice_amount=105000.0,  # Exceeds delivered value & PO
        )
        self.assertEqual(result["status"], "MISMATCH_HOLD")
        self.assertFalse(result["is_matched"])
        self.assertGreater(len(result["discrepancies"]), 0)

    def test_partial_grn_accepted_with_full_invoice_fails(self):
        # PO was for 100 units, but only 80 units accepted (value 80,000)
        # Vendor billed full 100,000
        result = perform_three_way_match(
            po_amount=100000.0,
            grn_accepted_qty=80,
            unit_price=1000.0,
            invoice_amount=100000.0,
        )
        self.assertEqual(result["status"], "MISMATCH_HOLD")
        self.assertFalse(result["is_matched"])

    def test_partial_grn_accepted_with_matching_partial_invoice_passes(self):
        # 80 units accepted, vendor billed for 80 units (80,000 <= PO 100,000)
        result = perform_three_way_match(
            po_amount=100000.0,
            grn_accepted_qty=80,
            unit_price=1000.0,
            invoice_amount=80000.0,
        )
        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["is_matched"])


if __name__ == "__main__":
    unittest.main()
