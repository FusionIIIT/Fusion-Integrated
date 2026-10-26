"""Tests for ELM application services, workflow transitions, and scoping.

Validates:
- EL-UC-001 / CW-EL-01: Application submission and validation
- EL-UC-002 / BR-EL-015: Substitute accept / decline flow
- EL-UC-003 / CW-EL-01: Review and recommendation
- EL-UC-004 / CW-EL-01: Sanction approval and rejection
- EL-UC-005 / CFR-EL-021: Application withdrawal
- Scoping and ownership security
"""
from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import modules.leave.tests._shim  # isort: skip # noqa: F401
from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.models import LeaveApplication, LeaveApplicationAudit
from modules.leave.selectors import scoping
from modules.leave.services import applications as app_service


class DummyActor:
    def __init__(self, user_id: int, permissions: set[str] | None = None):
        self.user_id = user_id
        self.permissions = permissions or set()

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return bool(self.permissions.intersection(codes))


class TestApplicationService(unittest.TestCase):
    """Test core service workflows and business rule checks."""

    def setUp(self):
        self.atomic_patcher = patch("django.db.transaction.atomic")
        self.mock_atomic = self.atomic_patcher.start()
        self.mock_atomic.return_value.__enter__.return_value = self.mock_atomic
        self.mock_atomic.return_value.__exit__.return_value = False

        self.applicant = DummyActor(user_id=101, permissions={"leave.application.create", "leave.application.view"})
        self.substitute = DummyActor(user_id=102, permissions={"leave.substitute.respond"})
        self.reviewer = DummyActor(user_id=201, permissions={"leave.application.review"})
        self.approver = DummyActor(user_id=301, permissions={"leave.application.approve"})

    def tearDown(self):
        self.atomic_patcher.stop()

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication, "save")
    def test_apply_leave_without_substitute_submits_directly(self, mock_save, mock_audit):
        app = app_service.apply_leave(
            actor=self.applicant,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),
            reason="Family function",
        )
        self.assertEqual(app.user_id, 101)
        self.assertEqual(app.category, "CL")
        self.assertEqual(app.status, "submitted")
        mock_save.assert_called_once()
        mock_audit.assert_called_once()

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication, "save")
    def test_apply_leave_with_substitute_awaits_substitute(self, mock_save, mock_audit):
        app = app_service.apply_leave(
            actor=self.applicant,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),
            substitute_id=102,
        )
        self.assertEqual(app.status, "awaiting_substitute")
        self.assertEqual(app.substitute_id, 102)

    def test_apply_leave_substitute_self_nomination_rejected(self):
        with self.assertRaises(BadRequestError) as ctx:
            app_service.apply_leave(
                actor=self.applicant,
                category="CL",
                start_date=date(2026, 11, 2),
                end_date=date(2026, 11, 4),
                substitute_id=101,  # same as applicant
            )
        self.assertEqual(ctx.exception.code, "invalid_substitute")

    def test_apply_leave_exceeding_annual_quota_rejected(self):
        with self.assertRaises(BadRequestError) as ctx:
            app_service.apply_leave(
                actor=self.applicant,
                category="CL",
                start_date=date(2026, 11, 2),
                end_date=date(2026, 11, 20),  # 15 working days > 8.0 CL quota
            )
        self.assertEqual(ctx.exception.code, "validation_error")

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication.objects, "get")
    def test_substitute_accept_moves_to_under_review(self, mock_get, mock_audit):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.substitute_id = 102
        dummy_app.status = "awaiting_substitute"
        mock_get.return_value = dummy_app

        res = app_service.respond_substitute(
            actor=self.substitute,
            application_id=1,
            action="accept",
            reason="Happy to cover classes.",
        )
        self.assertEqual(res.status, "under_review")
        dummy_app.save.assert_called_once()
        mock_audit.assert_called_once()

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication.objects, "get")
    def test_substitute_decline_moves_to_draft_per_br_el_015(self, mock_get, mock_audit):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.substitute_id = 102
        dummy_app.status = "awaiting_substitute"
        mock_get.return_value = dummy_app

        res = app_service.respond_substitute(
            actor=self.substitute,
            application_id=1,
            action="decline",
            reason="Prior commitment",
        )
        self.assertEqual(res.status, "draft")
        dummy_app.save.assert_called_once()

    @patch.object(LeaveApplication.objects, "get")
    def test_substitute_unauthorized_actor_rejected(self, mock_get):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.substitute_id = 102
        dummy_app.status = "awaiting_substitute"
        mock_get.return_value = dummy_app

        wrong_actor = DummyActor(user_id=999)
        with self.assertRaises(PermissionDeniedError):
            app_service.respond_substitute(
                actor=wrong_actor,
                application_id=1,
                action="accept",
            )

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication.objects, "get")
    def test_review_recommend_moves_to_awaiting_sanction(self, mock_get, mock_audit):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.status = "under_review"
        mock_get.return_value = dummy_app

        res = app_service.review_application(
            actor=self.reviewer,
            application_id=1,
            action="recommend",
            reason="Arrangements are in order.",
        )
        self.assertEqual(res.status, "awaiting_sanction")
        dummy_app.save.assert_called_once()
        mock_audit.assert_called_once()

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication.objects, "get")
    def test_review_reject_moves_to_rejected(self, mock_get, mock_audit):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.status = "under_review"
        mock_get.return_value = dummy_app

        res = app_service.review_application(
            actor=self.reviewer,
            application_id=1,
            action="reject",
            reason="Coverage insufficient.",
        )
        self.assertEqual(res.status, "rejected")
        dummy_app.save.assert_called_once()

    @patch.object(LeaveApplication.objects, "get")
    def test_review_without_permission_rejected(self, mock_get):
        with self.assertRaises(PermissionDeniedError):
            app_service.review_application(
                actor=self.applicant,
                application_id=1,
                action="recommend",
            )

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication.objects, "get")
    def test_sanction_approve_moves_to_approved(self, mock_get, mock_audit):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.status = "awaiting_sanction"
        mock_get.return_value = dummy_app

        res = app_service.sanction_application(
            actor=self.approver,
            application_id=1,
            action="approve",
        )
        self.assertEqual(res.status, "approved")
        dummy_app.save.assert_called_once()

    @patch.object(LeaveApplicationAudit.objects, "create")
    @patch.object(LeaveApplication.objects, "get")
    def test_withdraw_application_by_applicant(self, mock_get, mock_audit):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.user_id = 101
        dummy_app.status = "submitted"
        dummy_app.start_date = date(2099, 1, 1)  # Future date
        mock_get.return_value = dummy_app

        res = app_service.withdraw_application(
            actor=self.applicant,
            application_id=1,
            reason="Change in travel plans.",
        )
        self.assertEqual(res.status, "withdrawn")
        dummy_app.save.assert_called_once()

    @patch.object(LeaveApplication.objects, "get")
    def test_withdraw_other_users_application_rejected(self, mock_get):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.user_id = 999  # different user
        dummy_app.status = "submitted"
        dummy_app.start_date = date(2099, 1, 1)
        mock_get.return_value = dummy_app

        with self.assertRaises(PermissionDeniedError):
            app_service.withdraw_application(
                actor=self.applicant,
                application_id=1,
            )

    @patch.object(LeaveApplication.objects, "get")
    def test_withdraw_already_terminal_status_rejected(self, mock_get):
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.pk = 1
        dummy_app.user_id = 101
        dummy_app.status = "rejected"
        dummy_app.start_date = date(2099, 1, 1)
        mock_get.return_value = dummy_app

        with self.assertRaises(ConflictError):
            app_service.withdraw_application(
                actor=self.applicant,
                application_id=1,
            )


class TestScoping(unittest.TestCase):
    """Test ownership filtering and visibility security."""

    def test_is_approver_detection(self):
        approver = DummyActor(1, permissions={"leave.application.approve"})
        reviewer = DummyActor(2, permissions={"leave.application.review"})
        employee = DummyActor(3, permissions={"leave.application.create"})
        self.assertTrue(scoping.is_approver(approver))
        self.assertTrue(scoping.is_approver(reviewer))
        self.assertFalse(scoping.is_approver(employee))
        self.assertFalse(scoping.is_approver(None))


if __name__ == "__main__":
    unittest.main()
