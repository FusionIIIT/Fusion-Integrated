from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.elm.models import LeaveApplication, SubstituteConsent
from modules.elm.services.workflow import (
    LeaveWorkflowAction,
    LeaveWorkflowState,
    WorkflowTransitionError,
    transition,
)


class WorkflowServiceTests(TestCase):
    def actor(self, user_id=1, *permissions):
        granted = set(permissions)
        return SimpleNamespace(user_id=user_id, has_permission=lambda code: code in granted)

    def setUp(self):
        self.applicant = self.actor(
            1, "elm.leave_application.submit", "elm.leave_application.withdraw"
        )
        self.application = LeaveApplication.objects.create(
            user_id=1,
            category="CL",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=1),
            status=LeaveWorkflowState.DRAFT,
            requested_days=1.0,
            purpose="Vacation",
        )

    def set_state(self, state):
        self.application.status = state
        self.application.save(update_fields=["status"])

    def apply(self, action, actor=None, **kwargs):
        return transition(
            self.application.id,
            action,
            category="CL",
            actor=actor or self.applicant,
            **kwargs,
        )

    def test_submit_application(self):
        result = self.apply(LeaveWorkflowAction.SUBMIT)
        self.assertEqual(result.status, LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW)

    def test_withdraw_application(self):
        self.set_state(LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW)
        result = self.apply(LeaveWorkflowAction.WITHDRAW)
        self.assertEqual(result.status, LeaveWorkflowState.WITHDRAWN)

    def test_substitute_accept_and_decline(self):
        for action, expected in (
            (LeaveWorkflowAction.ACCEPT_SUBSTITUTE, LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW),
            (LeaveWorkflowAction.DECLINE_SUBSTITUTE, LeaveWorkflowState.APPLICANT_ACTION_REQUIRED),
        ):
            with self.subTest(action=action):
                self.application.substitute_consents.all().delete()
                self.set_state(LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE)
                SubstituteConsent.objects.create(application=self.application, substitute_user_id=2)
                actor = self.actor(2, "elm.substitute_consent.respond")
                result = self.apply(action, actor=actor)
                self.assertEqual(result.status, expected)

    def test_nominate_replacement(self):
        self.set_state(LeaveWorkflowState.APPLICANT_ACTION_REQUIRED)
        result = self.apply(LeaveWorkflowAction.NOMINATE_REPLACEMENT)
        self.assertEqual(result.status, LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE)

    def test_unit_head_approve_and_reject(self):
        for action, expected in (
            (LeaveWorkflowAction.UNIT_HEAD_APPROVE, LeaveWorkflowState.APPROVED),
            (LeaveWorkflowAction.UNIT_HEAD_REJECT, LeaveWorkflowState.REJECTED),
        ):
            with self.subTest(action=action):
                self.set_state(LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW)
                actor = self.actor(3, "elm.leave_application.review")
                result = self.apply(action, actor=actor)
                self.assertEqual(result.status, expected)

    def test_route_to_final_sanction(self):
        self.set_state(LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING)
        actor = self.actor(3, "elm.leave_application.route")
        result = self.apply(LeaveWorkflowAction.ROUTE_TO_FINAL_SANCTION, actor=actor)
        self.assertEqual(result.status, LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION)

    def test_final_approve_and_reject(self):
        for action, expected in (
            (LeaveWorkflowAction.FINAL_APPROVE, LeaveWorkflowState.APPROVED),
            (LeaveWorkflowAction.FINAL_REJECT, LeaveWorkflowState.REJECTED),
        ):
            with self.subTest(action=action):
                self.set_state(LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION)
                actor = self.actor(4, "elm.leave_application.finalize")
                result = self.apply(action, actor=actor)
                self.assertEqual(result.status, expected)

    def test_director_approve_and_reject(self):
        for action, expected in (
            (LeaveWorkflowAction.DIRECTOR_APPROVE, LeaveWorkflowState.APPROVED),
            (LeaveWorkflowAction.DIRECTOR_REJECT, LeaveWorkflowState.REJECTED),
        ):
            with self.subTest(action=action):
                self.set_state(LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION)
                actor = self.actor(4, "elm.leave_application.self_sanction")
                result = self.apply(action, actor=actor)
                self.assertEqual(result.status, expected)

    def test_denied_permission(self):
        with self.assertRaises(PermissionDeniedError):
            self.apply(LeaveWorkflowAction.SUBMIT, actor=self.actor(1))

    def test_non_owner_cannot_withdraw(self):
        self.set_state(LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW)
        with self.assertRaises(PermissionDeniedError):
            self.apply(
                LeaveWorkflowAction.WITHDRAW, actor=self.actor(2, "elm.leave_application.withdraw")
            )

    def test_non_nominated_substitute_cannot_respond(self):
        self.set_state(LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE)
        with self.assertRaises(PermissionDeniedError):
            self.apply(
                LeaveWorkflowAction.ACCEPT_SUBSTITUTE,
                actor=self.actor(2, "elm.substitute_consent.respond"),
            )

    def test_invalid_action_does_not_write_transition(self):
        with self.assertRaises(WorkflowTransitionError):
            self.apply(LeaveWorkflowAction.WITHDRAW)
        self.assertEqual(self.application.transitions.count(), 0)
