from django.test import SimpleTestCase

from modules.elm.models import Decision, LeaveRequest
from modules.elm.services import workflow as w

S = LeaveRequest.Status
Outcome = Decision.Outcome


class SubmitTests(SimpleTestCase):
    def test_substitute_required(self):
        self.assertEqual(w.submit(S.DRAFT, True, False), S.AWAITING_SUBSTITUTE)

    def test_normal_path(self):
        self.assertEqual(w.submit(S.DRAFT, False, False), S.AWAITING_UNIT_HEAD)

    def test_director_skips_unit_head(self):
        self.assertEqual(w.submit(S.DRAFT, False, True), S.AWAITING_DIRECTOR_SELF)

    def test_only_draft_can_submit(self):
        with self.assertRaises(w.TransitionError):
            w.submit(S.APPROVED, False, False)


class SubstituteTests(SimpleTestCase):
    def test_accept_releases_gate(self):
        self.assertEqual(w.substitute_accepted(S.AWAITING_SUBSTITUTE, False), S.AWAITING_UNIT_HEAD)

    def test_accept_director(self):
        self.assertEqual(
            w.substitute_accepted(S.AWAITING_SUBSTITUTE, True), S.AWAITING_DIRECTOR_SELF)

    def test_decline_keeps_gate_closed(self):
        self.assertEqual(w.substitute_declined(S.AWAITING_SUBSTITUTE), S.AWAITING_SUBSTITUTE)

    def test_cannot_accept_outside_gate(self):
        with self.assertRaises(w.TransitionError):
            w.substitute_accepted(S.AWAITING_UNIT_HEAD, False)


class UnitHeadTests(SimpleTestCase):
    def test_cl_approve_is_final(self):
        self.assertEqual(w.unit_head_decision(S.AWAITING_UNIT_HEAD, "CL", Outcome.APPROVED, True), S.APPROVED)

    def test_rh_reject_is_final(self):
        self.assertEqual(w.unit_head_decision(S.AWAITING_UNIT_HEAD, "RH", Outcome.REJECTED, False), S.REJECTED)

    def test_cl_cannot_be_recommended(self):
        with self.assertRaises(w.TransitionError):
            w.unit_head_decision(S.AWAITING_UNIT_HEAD, "CL", Outcome.RECOMMENDED, False)

    def test_el_not_recommended_does_not_reject(self):
        self.assertEqual(
            w.unit_head_decision(S.AWAITING_UNIT_HEAD, "EL", Outcome.NOT_RECOMMENDED, False),
            S.AWAITING_FINAL)

    def test_el_with_establishment_step(self):
        self.assertEqual(
            w.unit_head_decision(S.AWAITING_UNIT_HEAD, "VL", Outcome.RECOMMENDED, True),
            S.AWAITING_ESTABLISHMENT)

    def test_el_cannot_be_rejected_by_unit_head(self):
        with self.assertRaises(w.TransitionError):
            w.unit_head_decision(S.AWAITING_UNIT_HEAD, "EL", Outcome.REJECTED, False)


class FinalAndLifecycleTests(SimpleTestCase):
    def test_establishment_routes_to_final(self):
        self.assertEqual(w.establishment_routed(S.AWAITING_ESTABLISHMENT), S.AWAITING_FINAL)

    def test_final_approve_and_reject(self):
        self.assertEqual(w.final_decision(S.AWAITING_FINAL, Outcome.APPROVED), S.APPROVED)
        self.assertEqual(w.final_decision(S.AWAITING_FINAL, Outcome.REJECTED), S.REJECTED)

    def test_director_self_decision(self):
        self.assertEqual(w.final_decision(S.AWAITING_DIRECTOR_SELF, Outcome.APPROVED), S.APPROVED)

    def test_no_decision_after_withdrawal(self):
        with self.assertRaises(w.TransitionError):
            w.final_decision(S.WITHDRAWN, Outcome.APPROVED)

    def test_withdraw_pending(self):
        for state in w.PENDING:
            self.assertEqual(w.withdraw(state), S.WITHDRAWN)

    def test_withdraw_after_approval_refused(self):
        with self.assertRaises(w.TransitionError):
            w.withdraw(S.APPROVED)

    def test_modify_only_while_pending(self):
        self.assertTrue(w.can_modify(S.AWAITING_UNIT_HEAD))
        self.assertFalse(w.can_modify(S.APPROVED))
        self.assertFalse(w.can_modify(S.REJECTED))
