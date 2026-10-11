import unittest
from modules.elm.domain.state_machine import validate_transition, Status, PermissionDenied, InvalidTransition

class TestStateMachine(unittest.TestCase):
    def test_valid_transitions(self):
        # Test the exact 12 transitions and their required permissions
        valid_transitions = [
            (Status.DRAFT, Status.PENDING_UNIT_HEAD, {"elm.leave_request.create"}),
            (Status.PENDING_UNIT_HEAD, Status.APPROVED, {"elm.leave_request.approve"}),
            (Status.PENDING_UNIT_HEAD, Status.REJECTED, {"elm.leave_request.approve"}),
            (Status.PENDING_UNIT_HEAD, Status.PENDING_ESTABLISHMENT, {"elm.leave_request.approve"}),
            (Status.PENDING_ESTABLISHMENT, Status.PENDING_FINAL_SANCTION, {"elm.leave_request.approve"}),
            (Status.PENDING_ESTABLISHMENT, Status.REJECTED, {"elm.leave_request.approve"}),
            (Status.PENDING_FINAL_SANCTION, Status.APPROVED, {"elm.leave_request.approve"}),
            (Status.PENDING_FINAL_SANCTION, Status.REJECTED, {"elm.leave_request.approve"}),
            (Status.PENDING_UNIT_HEAD, Status.WITHDRAWN, {"elm.leave_request.update"}),
            (Status.PENDING_ESTABLISHMENT, Status.WITHDRAWN, {"elm.leave_request.update"}),
            (Status.PENDING_FINAL_SANCTION, Status.WITHDRAWN, {"elm.leave_request.update"}),
            (Status.APPROVED, Status.CANCELLED, {"elm.leave_request.update"}),
        ]

        for from_status, to_status, permissions in valid_transitions:
            validate_transition(from_status, to_status, permissions)

    def test_valid_transition_wildcard_permission(self):
        # Test a valid transition with wildcard permission "*"
        validate_transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, {"*"})

    def test_invalid_permissions(self):
        # Test that empty or incorrect permissions raise PermissionDenied
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, set())
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, {"incorrect.permission"})

    def test_invalid_transitions(self):
        # Test that an illegal transition raises InvalidTransition, even when wildcard permission is supplied
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.APPROVED, Status.WITHDRAWN, {"elm.leave_request.update"})
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.APPROVED, Status.WITHDRAWN, {"*"})

    def test_approved_withdraw(self):
        # Test that APPROVED status cannot be transitioned to WITHDRAWN
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.APPROVED, Status.WITHDRAWN, {"elm.leave_request.update"})

if __name__ == '__main__':
    unittest.main()
