"""Unit tests for OAP domain models and entity lifecycles."""
from __future__ import annotations

import datetime
from decimal import Decimal

from django.test import TestCase

from modules.oap.domain.exceptions import InvalidStateTransitionError
from modules.oap.models.bonafide import BonafidePurpose, BonafideRequest, BonafideStatus
from modules.oap.models.branch_change import BranchChangeRequest, BranchChangeStatus
from modules.oap.models.leave import LeaveType, RequestStatus, StudentLeaveRequest
from modules.oap.models.nodues import (
    DepartmentSignoffStatus,
    DepartmentType,
    NoDuesDepartmentalSignoff,
    NoDuesOverallStatus,
    NoDuesReason,
    NoDuesRequest,
)


class TestOAPModels(TestCase):
    def test_student_leave_lifecycle(self):
        req = StudentLeaveRequest.objects.create(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL,
            start_date=datetime.date(2026, 11, 25),
            end_date=datetime.date(2026, 11, 27),
            reason="Family commitment",
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.duration_days, 3)
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertIn("24BCS205", str(req))

        # Supervisor recommends
        req.recommend(supervisor_id="FAC001", remarks="Recommended")
        self.assertEqual(req.status, RequestStatus.RECOMMENDED)
        self.assertEqual(req.supervisor_id, "FAC001")

        with self.assertRaises(InvalidStateTransitionError):
            req.recommend(supervisor_id="FAC002")

        # HoD approves
        req.hod_approve(hod_id="HOD_CSE", remarks="Approved")
        self.assertEqual(req.status, RequestStatus.APPROVED)
        self.assertEqual(req.hod_id, "HOD_CSE")

        # Cannot modify approved leave
        with self.assertRaises(InvalidStateTransitionError):
            req.cancel()
        with self.assertRaises(InvalidStateTransitionError):
            req.hod_approve(hod_id="HOD_CSE")
        with self.assertRaises(InvalidStateTransitionError):
            req.hod_reject(hod_id="HOD_CSE")

    def test_leave_rejection_and_cancellation(self):
        req = StudentLeaveRequest.objects.create(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.SHORT,
            start_date=datetime.date(2026, 11, 25),
            end_date=datetime.date(2026, 11, 25),
            reason="Brief appointment",
            status=RequestStatus.PENDING,
        )
        req.hod_reject(hod_id="HOD_CSE", remarks="Rejected")
        self.assertEqual(req.status, RequestStatus.REJECTED)

        req2 = StudentLeaveRequest.objects.create(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.SHORT,
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 1),
            reason="Brief appointment",
            status=RequestStatus.PENDING,
        )
        req2.cancel()
        self.assertEqual(req2.status, RequestStatus.CANCELLED)

    def test_bonafide_issue_and_reject(self):
        req = BonafideRequest.objects.create(
            student_id="24BCS205",
            purpose=BonafidePurpose.BANK_LOAN,
            details="SBI Education Loan verification",
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertIsNone(req.certificate_number)
        self.assertIn("24BCS205", str(req))

        cert_num = req.approve_and_issue(
            issued_by="ADMIN_ACAD", remarks="Verified academic standing"
        )
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertTrue(cert_num.startswith("IIITDMJ/OAP/BONA/"))
        self.assertIsNotNone(req.issued_at)

        with self.assertRaises(InvalidStateTransitionError):
            req.approve_and_issue("ADMIN_2")
        with self.assertRaises(InvalidStateTransitionError):
            req.reject("ADMIN_2", "Duplicate")

        # Test bonafide rejection
        req2 = BonafideRequest.objects.create(
            student_id="24BCS205",
            purpose=BonafidePurpose.PASSPORT,
            details="Passport",
        )
        req2.reject(issued_by="ADMIN_ACAD", reason="Invalid document")
        self.assertEqual(req2.status, BonafideStatus.REJECTED)

    def test_no_dues_clearance(self):
        nd = NoDuesRequest.objects.create(
            student_id="24BCS205", reason=NoDuesReason.GRADUATION
        )
        self.assertEqual(nd.overall_status, NoDuesOverallStatus.PENDING)
        self.assertIn("24BCS205", str(nd))

        # Create signoffs
        s1 = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=nd,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.PENDING,
        )
        s2 = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=nd,
            department=DepartmentType.HOSTEL,
            status=DepartmentSignoffStatus.PENDING,
        )
        self.assertIn("LIBRARY", str(s1))

        s1.record_signoff(status=DepartmentSignoffStatus.CLEARED, signoff_by="LIB_OFFICER")
        self.assertEqual(s1.status, DepartmentSignoffStatus.CLEARED)
        self.assertEqual(nd.overall_status, NoDuesOverallStatus.PENDING)

        s2.record_signoff(status=DepartmentSignoffStatus.CLEARED, signoff_by="WARDEN")
        nd.check_and_finalize(admin_id="ACAD_ADMIN")
        nd.refresh_from_db()
        self.assertEqual(nd.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertTrue(nd.clearance_certificate_number.startswith("IIITDMJ/NODUES/"))

    def test_branch_change_verification_and_sanction(self):
        bc = BranchChangeRequest.objects.create(
            student_id="24BCS205",
            current_branch="ECE",
            preferred_branch_1="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=40,
            has_backlogs=False,
        )
        self.assertIn("24BCS205", str(bc))
        with self.assertRaises(InvalidStateTransitionError):
            bc.allocate_seat("CSE")
        with self.assertRaises(InvalidStateTransitionError):
            bc.sanction("DEAN")

        self.assertTrue(bc.verify_eligibility())
        self.assertEqual(bc.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

        bc.allocate_seat(allocated_branch="CSE")
        self.assertEqual(bc.status, BranchChangeStatus.ALLOCATED)

        bc.sanction(approved_by="DEAN_ACAD")
        self.assertEqual(bc.status, BranchChangeStatus.APPROVED)
        self.assertEqual(bc.allocated_branch, "CSE")

        # Ineligible branch change
        bc_ineligible = BranchChangeRequest.objects.create(
            student_id="24BCS999",
            current_branch="ME",
            preferred_branch_1="CSE",
            current_cpi=Decimal("6.50"),
            credits_completed=20,
            has_backlogs=True,
        )
        self.assertFalse(bc_ineligible.verify_eligibility())
        self.assertEqual(bc_ineligible.status, BranchChangeStatus.INELIGIBLE)
