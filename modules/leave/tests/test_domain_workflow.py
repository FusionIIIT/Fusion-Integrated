import unittest
from modules.leave.domain.workflow import (
    DRAFT,
    UNDER_REVIEW,
    APPROVED,
    REJECTED,
    SUBSTITUTE_PENDING,
    SUBSTITUTE_DECLINED,
    ESTABLISHMENT_REVIEW,
    SANCTION_REVIEW,
    WITHDRAWN,
    CANCEL_REQUESTED,
    CANCELLED,
    RESUMPTION_SUBMITTED,
    EXTENSION_REQUESTED,
    CLOSED,
    validate_transition,
    is_terminal_state,
    resolve_approval_chain
)

class TestDomainWorkflow(unittest.TestCase):
    def test_cl_no_substitute_path(self):
        self.assertTrue(validate_transition(DRAFT, UNDER_REVIEW))
        self.assertTrue(validate_transition(UNDER_REVIEW, APPROVED))

    def test_cl_unit_head_rejection(self):
        self.assertTrue(validate_transition(UNDER_REVIEW, REJECTED))

    def test_substitute_accepted_path(self):
        self.assertTrue(validate_transition(DRAFT, SUBSTITUTE_PENDING))
        self.assertTrue(validate_transition(SUBSTITUTE_PENDING, UNDER_REVIEW))
        self.assertTrue(validate_transition(UNDER_REVIEW, APPROVED))

    def test_substitute_declined_and_replacement_loop(self):
        self.assertTrue(validate_transition(SUBSTITUTE_PENDING, SUBSTITUTE_DECLINED))
        self.assertTrue(validate_transition(SUBSTITUTE_DECLINED, SUBSTITUTE_PENDING))

    def test_higher_sanction_path(self):
        self.assertTrue(validate_transition(UNDER_REVIEW, ESTABLISHMENT_REVIEW))
        self.assertTrue(validate_transition(ESTABLISHMENT_REVIEW, SANCTION_REVIEW))
        self.assertTrue(validate_transition(SANCTION_REVIEW, APPROVED))

    def test_higher_sanction_direct(self):
        self.assertTrue(validate_transition(UNDER_REVIEW, SANCTION_REVIEW))

    def test_withdrawals(self):
        self.assertTrue(validate_transition(SUBSTITUTE_PENDING, WITHDRAWN))
        self.assertTrue(validate_transition(UNDER_REVIEW, WITHDRAWN))
        self.assertTrue(validate_transition(SANCTION_REVIEW, WITHDRAWN))

    def test_cannot_withdraw_from_approved(self):
        with self.assertRaises(ValueError):
            validate_transition(APPROVED, WITHDRAWN)

    def test_cancellation(self):
        self.assertTrue(validate_transition(APPROVED, CANCEL_REQUESTED))
        self.assertTrue(validate_transition(CANCEL_REQUESTED, CANCELLED))
        self.assertTrue(validate_transition(CANCEL_REQUESTED, APPROVED))

    def test_extension(self):
        self.assertTrue(validate_transition(APPROVED, EXTENSION_REQUESTED))
        self.assertTrue(validate_transition(EXTENSION_REQUESTED, APPROVED))

    def test_resumption(self):
        self.assertTrue(validate_transition(APPROVED, RESUMPTION_SUBMITTED))
        self.assertTrue(validate_transition(RESUMPTION_SUBMITTED, CLOSED))

    def test_terminal_states(self):
        for s in [REJECTED, WITHDRAWN, CANCELLED, CLOSED]:
            self.assertTrue(is_terminal_state(s))
        self.assertFalse(is_terminal_state(APPROVED))

    def test_hierarchy_resolution(self):
        cl = resolve_approval_chain("CL")
        self.assertTrue(cl["unit_head_is_final"])
        el = resolve_approval_chain("EL")
        self.assertTrue(el["requires_higher_sanction"])
        is_director = resolve_approval_chain("DIRECTOR")
        self.assertEqual(is_director["final_authority"], "director_self")

if __name__ == '__main__':
    unittest.main()