"""Unit tests for ELM workflow state transitions according to STT specifications."""
import unittest
from modules.elm.domain.errors import InvalidStateTransitionError
from modules.elm.domain.workflow import validate_transition, LeaveState, LeaveEvent


class TestWorkflowTransitions(unittest.TestCase):
    def test_cl_without_substitute_submits_to_unit_head(self):
        next_state = validate_transition(
            current_state=LeaveState.DRAFT,
            event=LeaveEvent.SUBMIT,
            is_director=False,
            category="CL",
            substitute_required=False,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_UNIT_HEAD_REVIEW)

    def test_cl_with_substitute_submits_to_substitute_response(self):
        next_state = validate_transition(
            current_state=LeaveState.DRAFT,
            event=LeaveEvent.SUBMIT,
            is_director=False,
            category="CL",
            substitute_required=True,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_SUBSTITUTE_RESPONSE)

    def test_substitute_accept_moves_to_unit_head(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_SUBSTITUTE_RESPONSE,
            event=LeaveEvent.SUBSTITUTE_ACCEPT,
            is_director=False,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_UNIT_HEAD_REVIEW)

    def test_substitute_decline_moves_to_applicant_action(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_SUBSTITUTE_RESPONSE,
            event=LeaveEvent.SUBSTITUTE_DECLINE,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_APPLICANT_ACTION)

    def test_nominate_replacement_moves_back_to_substitute_response(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_APPLICANT_ACTION,
            event=LeaveEvent.NOMINATE_REPLACEMENT,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_SUBSTITUTE_RESPONSE)

    def test_unit_head_approve_cl_reaches_approved(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_UNIT_HEAD_REVIEW,
            event=LeaveEvent.UNIT_HEAD_APPROVE,
            category="CL",
        )
        self.assertEqual(next_state, LeaveState.APPROVED)

    def test_unit_head_reject_cl_reaches_rejected(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_UNIT_HEAD_REVIEW,
            event=LeaveEvent.UNIT_HEAD_REJECT,
            category="CL",
        )
        self.assertEqual(next_state, LeaveState.REJECTED)

    def test_higher_sanction_routes_to_establishment(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_UNIT_HEAD_REVIEW,
            event=LeaveEvent.UNIT_HEAD_RECOMMEND,
            category="EL",
            establishment_configured=True,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_ESTABLISHMENT_REVIEW)

    def test_establishment_verify_routes_to_sanction_authority(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_ESTABLISHMENT_REVIEW,
            event=LeaveEvent.ESTABLISHMENT_VERIFY,
        )
        self.assertEqual(next_state, LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW)

    def test_sanction_authority_approve_reaches_approved(self):
        next_state = validate_transition(
            current_state=LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW,
            event=LeaveEvent.SANCTION_APPROVE,
        )
        self.assertEqual(next_state, LeaveState.APPROVED)

    def test_immediate_withdrawal_from_pending_states(self):
        for pending_state in [
            LeaveState.AWAITING_SUBSTITUTE_RESPONSE,
            LeaveState.AWAITING_APPLICANT_ACTION,
            LeaveState.AWAITING_UNIT_HEAD_REVIEW,
            LeaveState.AWAITING_ESTABLISHMENT_REVIEW,
            LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW,
        ]:
            next_state = validate_transition(
                current_state=pending_state,
                event=LeaveEvent.WITHDRAW,
            )
            self.assertEqual(next_state, LeaveState.WITHDRAWN)

    def test_cannot_withdraw_already_approved_leave(self):
        with self.assertRaises(InvalidStateTransitionError):
            validate_transition(
                current_state=LeaveState.APPROVED,
                event=LeaveEvent.WITHDRAW,
            )

    def test_pre_start_cancellation_flow(self):
        s1 = validate_transition(
            current_state=LeaveState.APPROVED,
            event=LeaveEvent.REQUEST_CANCELLATION,
        )
        self.assertEqual(s1, LeaveState.AWAITING_CANCELLATION_REVIEW)

        s2 = validate_transition(
            current_state=LeaveState.AWAITING_CANCELLATION_REVIEW,
            event=LeaveEvent.APPROVE_CANCELLATION,
        )
        self.assertEqual(s2, LeaveState.CANCELLED)

    def test_director_self_sanction_without_substitute(self):
        next_state = validate_transition(
            current_state=LeaveState.DRAFT,
            event=LeaveEvent.SUBMIT,
            is_director=True,
            substitute_required=False,
        )
        self.assertEqual(next_state, LeaveState.APPROVED)


if __name__ == "__main__":
    unittest.main()
