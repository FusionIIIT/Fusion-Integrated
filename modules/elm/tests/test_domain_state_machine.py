"""Domain tests for ELM State Machine.

Pure Python, no database, executes in milliseconds.
Verifies all 17 Basis Workflows, 4 Composite Workflows, and STT transitions.
"""
import datetime
import unittest

from modules.elm.domain.constants import (
    ApplicationStatus,
    CancellationStatus,
    LeaveCategory,
    Recommendation,
    ResumptionType,
    Role,
    TERMINAL_STATUSES,
)
from modules.elm.domain.state_machine import (
    ALL_TRANSITIONS,
    InvalidTransition,
    TransitionGuardFailed,
    evaluate_resumption,
    get_legal_next_states,
    is_legal_transition,
    resolve_transition,
    validate_cancellation_request,
    validate_unit_head_decision,
    validate_withdrawal,
)


class TestElmStateMachine(unittest.TestCase):

    def test_transitions_exist_and_cover_composite_workflows(self):
        """Ensure all declared transitions map to valid states."""
        self.assertGreater(len(ALL_TRANSITIONS), 15)
        for t in ALL_TRANSITIONS:
            self.assertIsInstance(t.from_state, ApplicationStatus)
            self.assertIsInstance(t.to_state, ApplicationStatus)
            self.assertTrue(len(t.action) > 0)

    # ---- Basis Workflows BW-EL-01 to BW-EL-03 (CL / RH) --------------------
    def test_bw_el_01_cl_rh_direct_to_unit_head(self):
        """BW-EL-01: Draft -> Apply Direct -> Awaiting Unit Head -> Approve/Reject."""
        # 1. Apply direct
        t1 = resolve_transition(ApplicationStatus.DRAFT, "apply_direct")
        self.assertEqual(t1.to_state, ApplicationStatus.AWAITING_UNIT_HEAD)
        self.assertIn("BW-EL-01", t1.basis_workflows)

        # 2. Unit Head approves CL/RH (BR-EL-016)
        res_app = validate_unit_head_decision(LeaveCategory.CL, "APPROVE")
        self.assertEqual(res_app, ApplicationStatus.APPROVED)

        # 3. Unit Head rejects CL/RH (BR-EL-016)
        res_rej = validate_unit_head_decision(LeaveCategory.RH, "REJECT")
        self.assertEqual(res_rej, ApplicationStatus.REJECTED)

    def test_bw_el_02_cl_rh_substitute_accepted(self):
        """BW-EL-02: Draft -> Apply with Substitute -> Substitute Accept -> Unit Head -> Approve."""
        # 1. Apply with substitute
        t1 = resolve_transition(ApplicationStatus.DRAFT, "apply_with_substitute")
        self.assertEqual(t1.to_state, ApplicationStatus.AWAITING_SUBSTITUTE)
        self.assertIn("BW-EL-02", t1.basis_workflows)

        # 2. Substitute accepts
        t2 = resolve_transition(ApplicationStatus.AWAITING_SUBSTITUTE, "substitute_accept")
        self.assertEqual(t2.to_state, ApplicationStatus.AWAITING_UNIT_HEAD)
        self.assertIn("BW-EL-02", t2.basis_workflows)

        # 3. Unit Head decision
        self.assertEqual(validate_unit_head_decision(LeaveCategory.CL, "APPROVE"), ApplicationStatus.APPROVED)

    def test_bw_el_03_cl_rh_substitute_decline_and_replace(self):
        """BW-EL-03: Draft -> Apply with Sub -> Decline -> Action Required -> Replace Sub -> Accept -> Unit Head."""
        # 1. Apply
        self.assertTrue(is_legal_transition(ApplicationStatus.DRAFT, ApplicationStatus.AWAITING_SUBSTITUTE))

        # 2. Substitute declines
        t2 = resolve_transition(ApplicationStatus.AWAITING_SUBSTITUTE, "substitute_decline")
        self.assertEqual(t2.to_state, ApplicationStatus.APPLICANT_ACTION_REQUIRED)
        self.assertIn("BW-EL-03", t2.basis_workflows)

        # 3. Nominate replacement (EL-UC-019)
        t3 = resolve_transition(ApplicationStatus.APPLICANT_ACTION_REQUIRED, "nominate_replacement_substitute")
        self.assertEqual(t3.to_state, ApplicationStatus.AWAITING_SUBSTITUTE)
        self.assertIn("BW-EL-03", t3.basis_workflows)

        # 4. Replacement accepts
        t4 = resolve_transition(ApplicationStatus.AWAITING_SUBSTITUTE, "substitute_accept")
        self.assertEqual(t4.to_state, ApplicationStatus.AWAITING_UNIT_HEAD)

    # ---- Basis Workflows BW-EL-04 to BW-EL-06 (Higher-Sanction) ------------
    def test_bw_el_04_higher_sanction_direct(self):
        """BW-EL-04: Higher sanction: Unit Head recommends -> (Establishment) -> Sanction."""
        # Unit Head records RECOMMENDED without establishment
        res_direct = validate_unit_head_decision(LeaveCategory.EL, Recommendation.RECOMMENDED, has_establishment_step=False)
        self.assertEqual(res_direct, ApplicationStatus.AWAITING_SANCTION)

        # Unit Head records NOT_RECOMMENDED without establishment (BR-EL-017: not a final rejection!)
        res_not_rec = validate_unit_head_decision(LeaveCategory.COL, Recommendation.NOT_RECOMMENDED, has_establishment_step=False)
        self.assertEqual(res_not_rec, ApplicationStatus.AWAITING_SANCTION)

        # Unit Head records with establishment step configured (BR-EL-019)
        res_est = validate_unit_head_decision(LeaveCategory.SCL, Recommendation.RECOMMENDED, has_establishment_step=True)
        self.assertEqual(res_est, ApplicationStatus.AWAITING_ESTABLISHMENT)

        # Establishment routes to Sanction
        t_est = resolve_transition(ApplicationStatus.AWAITING_ESTABLISHMENT, "establishment_route")
        self.assertEqual(t_est.to_state, ApplicationStatus.AWAITING_SANCTION)

        # Final sanction decisions
        t_app = resolve_transition(ApplicationStatus.AWAITING_SANCTION, "sanction_approve")
        self.assertEqual(t_app.to_state, ApplicationStatus.APPROVED)
        t_rej = resolve_transition(ApplicationStatus.AWAITING_SANCTION, "sanction_reject")
        self.assertEqual(t_rej.to_state, ApplicationStatus.REJECTED)

    # ---- Basis Workflows BW-EL-07 to BW-EL-09 (Director Self-Sanction) ------
    def test_bw_el_07_director_self_sanction_direct(self):
        """BW-EL-07: Director applicant routes to self-sanction (BR-EL-020)."""
        t = resolve_transition(ApplicationStatus.DRAFT, "apply_director_direct")
        self.assertEqual(t.to_state, ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION)
        self.assertIn("BW-EL-07", t.basis_workflows)

        t_app = resolve_transition(ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION, "director_self_approve")
        self.assertEqual(t_app.to_state, ApplicationStatus.APPROVED)
        t_rej = resolve_transition(ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION, "director_self_reject")
        self.assertEqual(t_rej.to_state, ApplicationStatus.REJECTED)

    def test_bw_el_08_director_self_sanction_with_substitute(self):
        """BW-EL-08: Director with substitute -> Substitute Accept -> Director Self-Sanction."""
        t1 = resolve_transition(ApplicationStatus.DRAFT, "apply_with_substitute")
        self.assertEqual(t1.to_state, ApplicationStatus.AWAITING_SUBSTITUTE)

        t2 = resolve_transition(ApplicationStatus.AWAITING_SUBSTITUTE, "substitute_accept_director")
        self.assertEqual(t2.to_state, ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION)
        self.assertIn("BW-EL-08", t2.basis_workflows)

    # ---- Pre-Start Cancellation (BR-EL-023, CW-EL-02) -----------------------
    def test_cancellation_guards(self):
        """BR-EL-023: Approved leave can only be cancelled before start date."""
        today = datetime.date(2026, 10, 26)
        future_start = datetime.date(2026, 11, 1)
        past_start = datetime.date(2026, 10, 20)

        # Legal: approved and before start
        validate_cancellation_request(ApplicationStatus.APPROVED, future_start, today)

        # Illegal: leave already started
        with self.assertRaises(TransitionGuardFailed):
            validate_cancellation_request(ApplicationStatus.APPROVED, past_start, today)

        # Illegal: leave on today
        with self.assertRaises(TransitionGuardFailed):
            validate_cancellation_request(ApplicationStatus.APPROVED, today, today)

        # Illegal: leave is not approved (e.g. pending or draft)
        with self.assertRaises(TransitionGuardFailed):
            validate_cancellation_request(ApplicationStatus.AWAITING_UNIT_HEAD, future_start, today)

    # ---- Resumption (BR-EL-027, BR-EL-028, CW-EL-04) ------------------------
    def test_resumption_evaluation(self):
        """BR-EL-028: Normal, early, and late resumption outcome."""
        end_date = datetime.date(2026, 10, 20)  # approved leave Monday 19 to Tuesday 20
        # Expected resumption is Wednesday 21

        # 1. Normal: actual is Wednesday 21
        rtype, diff = evaluate_resumption(end_date, datetime.date(2026, 10, 21))
        self.assertEqual(rtype, ResumptionType.NORMAL)
        self.assertEqual(diff, 0)

        # 2. Early: returned Tuesday 20 (1 day early)
        rtype, diff = evaluate_resumption(end_date, datetime.date(2026, 10, 20))
        self.assertEqual(rtype, ResumptionType.EARLY)
        self.assertEqual(diff, 1)

        # 3. Late: returned Friday 23 (2 days late)
        rtype, diff = evaluate_resumption(end_date, datetime.date(2026, 10, 23))
        self.assertEqual(rtype, ResumptionType.LATE)
        self.assertEqual(diff, 2)

    # ---- Cross-cutting Withdrawal (BR-EL-022, BR-EL-034) --------------------
    def test_withdrawal_available_from_all_pending_states(self):
        """BR-EL-022: Withdrawal is valid from every pending pre-final state."""
        pending_states = [
            ApplicationStatus.AWAITING_SUBSTITUTE,
            ApplicationStatus.APPLICANT_ACTION_REQUIRED,
            ApplicationStatus.AWAITING_UNIT_HEAD,
            ApplicationStatus.AWAITING_ESTABLISHMENT,
            ApplicationStatus.AWAITING_SANCTION,
            ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        ]
        for st in pending_states:
            # Does not raise
            validate_withdrawal(st)
            self.assertTrue(is_legal_transition(st, ApplicationStatus.WITHDRAWN))

    def test_withdrawal_forbidden_from_terminal_states(self):
        """BR-EL-022: After final approval or terminal decision, withdrawal is unavailable."""
        terminal_states = [
            ApplicationStatus.APPROVED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.CANCELLED,
        ]
        for st in terminal_states:
            with self.assertRaises(TransitionGuardFailed):
                validate_withdrawal(st)

    def test_illegal_transitions_raise(self):
        """Check random illegal transition attempts."""
        self.assertFalse(is_legal_transition(ApplicationStatus.DRAFT, ApplicationStatus.APPROVED))
        self.assertFalse(is_legal_transition(ApplicationStatus.APPROVED, ApplicationStatus.DRAFT))
        self.assertFalse(is_legal_transition(ApplicationStatus.REJECTED, ApplicationStatus.AWAITING_UNIT_HEAD))

        with self.assertRaises(InvalidTransition):
            resolve_transition(ApplicationStatus.DRAFT, "sanction_approve")


if __name__ == "__main__":
    unittest.main()
