from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from modules.elm.models import LeaveApplication
from modules.elm.services.authz import require
from modules.elm.services.workflow import LeaveWorkflowAction, LeaveWorkflowState, transition


class WorkflowServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.application = LeaveApplication.objects.create(
            user=self.user,
            category="CL",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=1),
            status=LeaveWorkflowState.DRAFT,
        )

    def test_submit_application(self):
        require(self.user, "elm.submit_application")
        transition(self.application.id, LeaveWorkflowAction.SUBMIT, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW)

    def test_withdraw_application(self):
        require(self.user, "elm.withdraw_application")
        transition(self.application.id, LeaveWorkflowAction.WITHDRAW, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.WITHDRAWN)

    def test_accept_substitute(self):
        require(self.user, "elm.respond_to_substitute")
        self.application.status = LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.ACCEPT_SUBSTITUTE, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW)

    def test_decline_substitute(self):
        require(self.user, "elm.respond_to_substitute")
        self.application.status = LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.DECLINE_SUBSTITUTE, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.APPLICANT_ACTION_REQUIRED)

    def test_nominate_replacement(self):
        require(self.user, "elm.respond_to_substitute")
        self.application.status = LeaveWorkflowState.APPLICANT_ACTION_REQUIRED
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.NOMINATE_REPLACEMENT, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE)

    def test_unit_head_approve(self):
        require(self.user, "elm.review_by_unit_head")
        self.application.status = LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.UNIT_HEAD_APPROVE, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.APPROVED)

    def test_unit_head_reject(self):
        require(self.user, "elm.review_by_unit_head")
        self.application.status = LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.UNIT_HEAD_REJECT, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.REJECTED)

    def test_route_to_establishment(self):
        require(self.user, "elm.route_to_establishment")
        self.application.status = LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.ROUTE_TO_FINAL_SANCTION, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING)

    def test_final_approve(self):
        require(self.user, "elm.finalize_sanction")
        self.application.status = LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.FINAL_APPROVE, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.APPROVED)

    def test_final_reject(self):
        require(self.user, "elm.finalize_sanction")
        self.application.status = LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.FINAL_REJECT, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.REJECTED)

    def test_director_approve(self):
        require(self.user, "elm.self_sanction_by_director")
        self.application.status = LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.DIRECTOR_APPROVE, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.APPROVED)

    def test_director_reject(self):
        require(self.user, "elm.self_sanction_by_director")
        self.application.status = LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION
        self.application.save()
        transition(self.application.id, LeaveWorkflowAction.DIRECTOR_REJECT, category="CL", actor=self.user)
        self.assertEqual(self.application.status, LeaveWorkflowState.REJECTED)
