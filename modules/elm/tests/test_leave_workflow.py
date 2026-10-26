from datetime import date

from django.test import TestCase

from modules.directory.models import UserRef
from modules.elm.models import LeaveApplication, LeaveType, LeaveBalance, SubstituteNominee
from modules.elm.services.leave_application_service import (
    create_leave_application,
    respond_to_substitute_request,
    nominate_replacement_substitute,
    approve_leave_application,
    unit_head_review,
)


class TestLeaveWorkflow(TestCase):
    def setUp(self):
        # Create UserRef objects using their actual fields (user_id is the PK)
        self.applicant = UserRef.objects.create(
            user_id=1001,
            username="applicant",
            display_name="Test Applicant",
            kind="staff",
            is_active=True
        )
        self.substitute = UserRef.objects.create(
            user_id=1002,
            username="substitute",
            display_name="Test Substitute",
            kind="staff",
            is_active=True
        )
        self.new_substitute = UserRef.objects.create(
            user_id=1003,
            username="new_substitute",
            display_name="Test New Substitute",
            kind="staff",
            is_active=True
        )
        self.unit_head = UserRef.objects.create(
            user_id=2001,
            username="unit_head",
            display_name="Test Unit Head",
            kind="staff",
            is_active=True,
        )
        
        self.leave_type = LeaveType.objects.create(code="CL", label="Casual Leave")
        self.leave_balance = LeaveBalance.objects.create(
            user=self.applicant, 
            leave_type=self.leave_type, 
            balance=8.0,
        )
        
    def test_substitute_decline_and_replacement_workflow(self):
        # 1. Create Application
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=self.substitute.user_id,
        )
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_SUBSTITUTE_RESPONSE)
        self.assertEqual(SubstituteNominee.objects.filter(status=SubstituteNominee.NominationStatus.PENDING).count(), 1)
        
        # Refresh from DB to check balance (proves BR-EL-023: no deduction at creation)
        self.leave_balance.refresh_from_db()
        self.assertEqual(self.leave_balance.balance, 8.0)

        # 2. Substitute Declines
        nominee = application.substitutenominee_set.first()
        response = respond_to_substitute_request(
            nominee_id=nominee.id,
            user_id=self.substitute.user_id,
            response='declined',
        )
        self.assertTrue(response["success"])
        nominee.refresh_from_db()
        self.assertEqual(nominee.status, SubstituteNominee.NominationStatus.DECLINED)
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.APPLICANT_ACTION_REQUIRED)

        # 3. Nominate Replacement
        response = nominate_replacement_substitute(
            application_id=application.id,
            applicant_user_id=self.applicant.user_id,
            new_substitute_user_id=self.new_substitute.user_id,
        )
        self.assertTrue(response["success"])
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_SUBSTITUTE_RESPONSE)
        self.assertEqual(SubstituteNominee.objects.count(), 2)

        # 4. Replacement Accepts
        new_nominee = application.substitutenominee_set.filter(
            status=SubstituteNominee.NominationStatus.PENDING
        ).first()
        response = respond_to_substitute_request(
            nominee_id=new_nominee.id,
            user_id=self.new_substitute.user_id,
            response='accepted',
        )
        self.assertTrue(response["success"])
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW)

    def test_balance_deduction_on_approval(self):
        # Setup: Create application using create_leave_application with no substitute
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=None,
        )
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW)
        self.assertEqual(SubstituteNominee.objects.filter(status=SubstituteNominee.NominationStatus.PENDING).count(), 0)
        
        # Refresh from DB to check balance (proves BR-EL-023: no deduction at creation)
        self.leave_balance.refresh_from_db()
        self.assertEqual(self.leave_balance.balance, 8.0)

        # Call approve_leave_application(application.id, approver_user_id)
        response = approve_leave_application(application.id, approver_user_id=1)
        self.assertTrue(response["success"])
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.APPROVED)
        self.assertEqual(application.final_decision, 'approved')
        self.assertIsNotNone(application.final_decision_date)

        # Assert: LeaveBalance is now 6.0 (2 days deducted for Oct 1-2)
        self.leave_balance.refresh_from_db()
        self.assertEqual(self.leave_balance.balance, 6.0)
        
    def test_unit_head_review_cl_approval(self):
        """Test CL/RH approval path: Unit Head is final authority (BR-EL-016)."""
        # Create application with no substitute -> goes to AWAITING_UNIT_HEAD_REVIEW
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=None,
        )
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW)

        # Unit Head approves -> should become APPROVED
        response = unit_head_review(
            application_id=application.id,
            unit_head_user_id=self.unit_head.user_id,
            decision='approved',
            recommendation='',
        )
        self.assertTrue(response['success'])

        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.APPROVED)

    def test_unit_head_review_cl_rejection(self):
        """Test CL/RH rejection path: Unit Head can reject (BR-EL-016)."""
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=None,
        )
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW)

        # Unit Head rejects -> should become REJECTED
        response = unit_head_review(
            application_id=application.id,
            unit_head_user_id=self.unit_head.user_id,
            decision='rejected',
            recommendation='',
        )
        self.assertTrue(response['success'])

        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.REJECTED)
        
    def test_unit_head_review_higher_sanction_recommendation(self):
        """Test higher-sanction path: Unit Head records recommendation, not final decision (BR-EL-017)."""
        # Create an EL (Earned Leave) type - higher-sanction leave
        el_type = LeaveType.objects.create(code="EL", label="Earned Leave")
        LeaveBalance.objects.create(user=self.applicant, leave_type=el_type, balance=30.0)

        # Create application with no substitute -> goes to AWAITING_UNIT_HEAD_REVIEW
        application = create_leave_application(
            user=self.applicant,
            leave_type=el_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 5),
            is_half_day=False,
            current_balance=30.0,
            existing_leaves=[],
            substitute_user_id=None,
        )
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_UNIT_HEAD_REVIEW)

        # Unit Head records recommendation (not final decision)
        response = unit_head_review(
            application_id=application.id,
            unit_head_user_id=self.unit_head.user_id,
            decision='recommended',
            recommendation='Recommended',
        )
        self.assertTrue(response['success'])

        application.refresh_from_db()
        # Should route to awaiting final sanction, NOT approved
        self.assertEqual(application.status, LeaveApplication.Status.AWAITING_FINAL_SANCTION_DECISION)
        # Recommendation should be recorded
        self.assertEqual(application.unit_head_recommendation, 'Recommended')
        # Final decision should NOT be set yet (that's the Sanctioning Authority's job)
        self.assertEqual(application.final_decision, '')
        self.assertIsNone(application.final_decision_date)
        
    def test_substitute_cannot_be_applicant(self):
        """Test BR-EL-014: Substitute must not be the applicant."""
        with self.assertRaises(ValueError) as context:
            create_leave_application(
                user=self.applicant,
                leave_type=self.leave_type,
                start_date=date(2023, 10, 1),
                end_date=date(2023, 10, 2),
                is_half_day=False,
                current_balance=8.0,
                existing_leaves=[],
                substitute_user_id=self.applicant.user_id,  # Applicant as substitute
            )
        self.assertIn('Substitute cannot be the applicant', str(context.exception))
        
    def test_cannot_respond_to_already_responded_nomination(self):
        """Test that a nominee cannot respond twice to the same nomination."""
        # Create application with substitute
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=self.substitute.user_id,
        )
        
        # First response (accept)
        nominee = application.substitutenominee_set.first()
        response1 = respond_to_substitute_request(
            nominee_id=nominee.id,
            user_id=self.substitute.user_id,
            response='accepted',
        )
        self.assertTrue(response1['success'])
        
        # Second response (should fail - already responded)
        response2 = respond_to_substitute_request(
            nominee_id=nominee.id,
            user_id=self.substitute.user_id,
            response='declined',
        )
        self.assertFalse(response2['success'])
        self.assertIn('not pending', response2['message'])

    def test_cannot_nominate_replacement_in_wrong_state(self):
        """Test that replacement nomination only works in APPLICANT_ACTION_REQUIRED state."""
        # Create application with no substitute -> goes to AWAITING_UNIT_HEAD_REVIEW
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=None,
        )
        
        # Try to nominate replacement (should fail - wrong state)
        response = nominate_replacement_substitute(
            application_id=application.id,
            applicant_user_id=self.applicant.user_id,
            new_substitute_user_id=self.new_substitute.user_id,
        )
        self.assertFalse(response['success'])
        self.assertIn('correct state', response['message'])

    def test_only_applicant_can_nominate_replacement(self):
        """Test that only the applicant can nominate a replacement substitute."""
        # Create application with substitute
        application = create_leave_application(
            user=self.applicant,
            leave_type=self.leave_type,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 2),
            is_half_day=False,
            current_balance=8.0,
            existing_leaves=[],
            substitute_user_id=self.substitute.user_id,
        )
        
        # Substitute declines
        nominee = application.substitutenominee_set.first()
        respond_to_substitute_request(
            nominee_id=nominee.id,
            user_id=self.substitute.user_id,
            response='declined',
        )
        
        # Try to nominate replacement as someone other than applicant (should fail)
        response = nominate_replacement_substitute(
            application_id=application.id,
            applicant_user_id=self.substitute.user_id,  # Wrong user
            new_substitute_user_id=self.new_substitute.user_id,
        )
        self.assertFalse(response['success'])
        self.assertIn('Only the applicant', response['message'])
