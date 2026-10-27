import unittest
from modules.elm.domain.state_machine import (
    validate_transition,
    Status,
    PermissionDenied,
    InvalidTransition,
    TRANSITIONS,
)


class TestStateMachine(unittest.TestCase):
    def test_all_transitions_have_permissions(self):
        # Every transition in TRANSITIONS must have non-empty permission
        for t in TRANSITIONS:
            self.assertTrue(t.permission.startswith("elm.leave_request."))
            validate_transition(t.from_status, t.to_status, {t.permission})
            validate_transition(t.from_status, t.to_status, {"*"})

    def test_substitute_consent_pipeline(self):
        # Submission requiring substitute
        validate_transition(Status.DRAFT, Status.AWAITING_SUBSTITUTE_RESPONSE, {"elm.leave_request.create"})
        # Substitute accepts -> Unit Head review
        validate_transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.PENDING_UNIT_HEAD, {"elm.leave_request.update"})
        # Substitute declines -> applicant action required
        validate_transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.APPLICANT_ACTION_REQUIRED, {"elm.leave_request.update"})
        # Replacement nominated -> back to awaiting substitute response
        validate_transition(Status.APPLICANT_ACTION_REQUIRED, Status.AWAITING_SUBSTITUTE_RESPONSE, {"elm.leave_request.update"})

    def test_director_self_sanction_pipeline(self):
        # Director apply with no substitute required
        validate_transition(Status.DRAFT, Status.AWAITING_DIRECTOR_SELF_SANCTION, {"elm.leave_request.create"})
        # Substitute accepts for Director
        validate_transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.AWAITING_DIRECTOR_SELF_SANCTION, {"elm.leave_request.update"})
        # Director self-sanction approve / reject
        validate_transition(Status.AWAITING_DIRECTOR_SELF_SANCTION, Status.APPROVED, {"elm.leave_request.approve"})
        validate_transition(Status.AWAITING_DIRECTOR_SELF_SANCTION, Status.REJECTED, {"elm.leave_request.approve"})

    def test_cancellation_pipeline(self):
        # Defect fixed: APPROVED cannot jump directly to CANCELLED
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.APPROVED, Status.CANCELLED, {"*"})

        # Valid cancellation progression:
        # 1. Employee requests cancellation of approved leave before start
        validate_transition(Status.APPROVED, Status.CANCELLATION_PENDING_UNIT_HEAD, {"elm.leave_request.update"})
        # 2. Unit Head approves cancellation -> CANCELLED
        validate_transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.CANCELLED, {"elm.leave_request.approve"})
        # 3. Unit Head rejects cancellation -> APPROVED (unchanged)
        validate_transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.APPROVED, {"elm.leave_request.approve"})
        # 4. Higher-sanction cancellation routing
        validate_transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.CANCELLATION_PENDING_ESTABLISHMENT, {"elm.leave_request.approve"})
        validate_transition(Status.CANCELLATION_PENDING_ESTABLISHMENT, Status.CANCELLATION_PENDING_FINAL_DECISION, {"elm.leave_request.approve"})
        validate_transition(Status.CANCELLATION_PENDING_FINAL_DECISION, Status.CANCELLED, {"elm.leave_request.approve"})

    def test_immediate_withdrawal_from_all_pending_states(self):
        # BR-EL-022: pending request withdrawable from any pre-final state
        pending_states = [
            Status.AWAITING_SUBSTITUTE_RESPONSE,
            Status.APPLICANT_ACTION_REQUIRED,
            Status.PENDING_UNIT_HEAD,
            Status.PENDING_ESTABLISHMENT,
            Status.PENDING_FINAL_SANCTION,
            Status.AWAITING_DIRECTOR_SELF_SANCTION,
        ]
        for state in pending_states:
            validate_transition(state, Status.WITHDRAWN, {"elm.leave_request.update"})

    def test_terminal_states_cannot_withdraw(self):
        # BR-EL-022: after final approval/rejection/cancellation, withdrawal is unavailable
        for terminal in [Status.APPROVED, Status.REJECTED, Status.CANCELLED, Status.WITHDRAWN]:
            with self.assertRaises(InvalidTransition):
                validate_transition(terminal, Status.WITHDRAWN, {"*"})

    def test_invalid_permissions(self):
        # Test that empty or incorrect permissions raise PermissionDenied on valid transitions
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, set())
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, {"incorrect.permission"})


if __name__ == "__main__":
    unittest.main()
