import unittest

from modules.elm.domain import (
    APPLICANT_ACTION_REQUIRED,
    APPROVED,
    AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_FINAL_SANCTION,
    AWAITING_SUBSTITUTE_RESPONSE,
    AWAITING_UNIT_HEAD_REVIEW,
    REJECTED,
    WITHDRAWN,
    InvalidTransition,
    initial_state,
    transition,
)


class TestStateMachine(unittest.TestCase):
    def test_initial_state(self):
        self.assertEqual(initial_state(True, False), AWAITING_SUBSTITUTE_RESPONSE)
        self.assertEqual(initial_state(False, True), AWAITING_DIRECTOR_SELF_SANCTION)
        self.assertEqual(initial_state(False, False), AWAITING_UNIT_HEAD_REVIEW)

    def test_substitute_accept(self):
        self.assertEqual(
            transition(
                AWAITING_SUBSTITUTE_RESPONSE, "substitute_accept", applicant_is_director=True
            ),
            AWAITING_DIRECTOR_SELF_SANCTION,
        )
        self.assertEqual(
            transition(
                AWAITING_SUBSTITUTE_RESPONSE, "substitute_accept", applicant_is_director=False
            ),
            AWAITING_UNIT_HEAD_REVIEW,
        )

    def test_substitute_decline(self):
        self.assertEqual(
            transition(AWAITING_SUBSTITUTE_RESPONSE, "substitute_decline"),
            APPLICANT_ACTION_REQUIRED,
        )

    def test_nominate_replacement(self):
        self.assertEqual(
            transition(APPLICANT_ACTION_REQUIRED, "nominate_replacement"),
            AWAITING_SUBSTITUTE_RESPONSE,
        )

    def test_unit_head_approve_reject(self):
        self.assertEqual(transition(AWAITING_UNIT_HEAD_REVIEW, "approve", category="CL"), APPROVED)
        self.assertEqual(transition(AWAITING_UNIT_HEAD_REVIEW, "reject", category="RH"), REJECTED)
        with self.assertRaises(InvalidTransition):
            transition(AWAITING_UNIT_HEAD_REVIEW, "approve", category="EL")

    def test_unit_head_recommend(self):
        self.assertEqual(
            transition(
                AWAITING_UNIT_HEAD_REVIEW, "recommend", category="EL", establishment_configured=True
            ),
            AWAITING_ESTABLISHMENT_ROUTING,
        )
        self.assertEqual(
            transition(
                AWAITING_UNIT_HEAD_REVIEW,
                "recommend",
                category="EL",
                establishment_configured=False,
            ),
            AWAITING_FINAL_SANCTION,
        )
        with self.assertRaises(InvalidTransition):
            transition(AWAITING_UNIT_HEAD_REVIEW, "recommend", category="CL")

    def test_route(self):
        self.assertEqual(
            transition(AWAITING_ESTABLISHMENT_ROUTING, "route"), AWAITING_FINAL_SANCTION
        )

    def test_final_sanction_approve_reject(self):
        self.assertEqual(transition(AWAITING_FINAL_SANCTION, "approve"), APPROVED)
        self.assertEqual(transition(AWAITING_DIRECTOR_SELF_SANCTION, "reject"), REJECTED)

    def test_withdraw(self):
        self.assertEqual(transition(AWAITING_UNIT_HEAD_REVIEW, "withdraw"), WITHDRAWN)
        self.assertEqual(transition(AWAITING_FINAL_SANCTION, "withdraw"), WITHDRAWN)

    def test_invalid_transitions(self):
        with self.assertRaises(InvalidTransition):
            transition(APPROVED, "approve")
        with self.assertRaises(InvalidTransition):
            transition(WITHDRAWN, "withdraw")
        with self.assertRaises(InvalidTransition):
            transition(AWAITING_UNIT_HEAD_REVIEW, "route")


if __name__ == "__main__":
    unittest.main()
