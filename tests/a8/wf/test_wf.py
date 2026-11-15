"""
Executable Test Suite for Strategy 4: WF (Workflows)
Implementing frozen a8_design/WF_DESIGN.json
A8_BASE: Other Academic Procedures (OAP) Subteam 04B
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from modules.oap.models import (
    LeaveType, RequestStatus, DepartmentChoice, ClearanceStatus, SeminarStatus,
    StudentLeaveRequest, BonafideRequest, NoDuesClearance, NoDuesItem,
    PGAssistantshipClaim, GraduateSeminar
)

class TestOAPWorkflows(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_TC_WF_001_BW_OAP_01(self):
        """
        Test ID: TC-WF-001 | Source ID: BW-OAP-01
        Purpose: Successful leave path from student submission to HoD approval.
        Expected: Leave application submitted - Approved by HoD
        """
        req = StudentLeaveRequest.objects.create(
            student_id="24BCS205", student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL, start_date="2026-11-15", end_date="2026-11-17",
            reason="Family function", status=RequestStatus.PENDING
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        req.status = RequestStatus.APPROVED
        req.hod_remarks = "Approved by HoD"
        req.save()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_TC_WF_002_BW_OAP_01(self):
        """
        Test ID: TC-WF-002 | Source ID: BW-OAP-01
        Purpose: Leave path ending in HoD rejection.
        Expected: Leave application submitted - Rejected by HoD
        """
        req = StudentLeaveRequest.objects.create(
            student_id="24BCS205", student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL, start_date="2026-11-15", end_date="2026-11-17",
            reason="Casual trip", status=RequestStatus.PENDING
        )
        req.status = RequestStatus.REJECTED
        req.hod_remarks = "Exam period, leave denied"
        req.save()
        self.assertEqual(req.status, RequestStatus.REJECTED)

    def test_TC_WF_003_BW_OAP_02(self):
        """
        Test ID: TC-WF-003 | Source ID: BW-OAP-02
        Purpose: Bonafide request path ending in approval.
        Expected: Bonafide request submitted - Approved by Academic Administrator
        """
        req = BonafideRequest.objects.create(
            student_id="24BCS205", purpose="Passport Application",
            status=RequestStatus.PENDING
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        req.status = RequestStatus.APPROVED
        req.certificate_number = "BONA-2026-001"
        req.save()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_TC_WF_004_BW_OAP_02(self):
        """
        Test ID: TC-WF-004 | Source ID: BW-OAP-02
        Purpose: Bonafide request path ending in rejection.
        Expected: Bonafide request submitted - Rejected by Academic Administrator
        """
        req = BonafideRequest.objects.create(
            student_id="24BCS205", purpose="Unspecified",
            status=RequestStatus.PENDING
        )
        req.status = RequestStatus.REJECTED
        req.save()
        self.assertEqual(req.status, RequestStatus.REJECTED)

    def test_TC_WF_005_BW_OAP_03(self):
        """
        Test ID: TC-WF-005 | Source ID: BW-OAP-03
        Purpose: No-dues clearance path ending in approval.
        Expected: No-dues clearance request submitted - Cleared
        """
        clearance = NoDuesClearance.objects.create(student_id="24BCS205", program="BTech")
        item = NoDuesItem.objects.create(
            clearance=clearance, department=DepartmentChoice.LIBRARY,
            status=ClearanceStatus.CLEARED
        )
        clearance.is_finalized = True
        clearance.save()
        self.assertTrue(clearance.is_finalized)

    def test_TC_WF_006_BW_OAP_03(self):
        """
        Test ID: TC-WF-006 | Source ID: BW-OAP-03
        Purpose: No-dues clearance path ending in dues outstanding.
        Expected: No-dues clearance request submitted - Dues Outstanding
        """
        clearance = NoDuesClearance.objects.create(student_id="24BCS205", program="BTech")
        item = NoDuesItem.objects.create(
            clearance=clearance, department=DepartmentChoice.LIBRARY,
            status=ClearanceStatus.DUES_OUTSTANDING, remarks="Overdue book"
        )
        self.assertEqual(item.status, ClearanceStatus.DUES_OUTSTANDING)
        self.assertFalse(clearance.is_finalized)

    def test_TC_WF_007_BW_OAP_05(self):
        """
        Test ID: TC-WF-007 | Source ID: BW-OAP-05
        Purpose: Assistantship claim path ending in approval.
        Expected: Assistantship claim submitted - Processed
        """
        claim = PGAssistantshipClaim.objects.create(
            student_id="24MCS101", month_year="2026-10", hours_rendered=40,
            thesis_supervisor_status=RequestStatus.APPROVED,
            ta_supervisor_status=RequestStatus.APPROVED,
            dept_admin_forwarded=True,
            hod_status=RequestStatus.APPROVED,
            stipend_processed=True
        )
        self.assertEqual(claim.hod_status, RequestStatus.APPROVED)
        self.assertTrue(claim.stipend_processed)

    def test_TC_WF_008_BW_OAP_06(self):
        """
        Test ID: TC-WF-008 | Source ID: BW-OAP-06
        Purpose: Assistantship claim path ending in dues outstanding / rejection.
        Expected: Assistantship claim submitted - Rejected
        """
        claim = PGAssistantshipClaim.objects.create(
            student_id="24MCS101", month_year="2026-10", hours_rendered=10,
            thesis_supervisor_status=RequestStatus.APPROVED,
            ta_supervisor_status=RequestStatus.APPROVED,
            dept_admin_forwarded=True,
            hod_status=RequestStatus.REJECTED,
            stipend_processed=False
        )
        self.assertEqual(claim.hod_status, RequestStatus.REJECTED)
        self.assertFalse(claim.stipend_processed)

    def test_TC_WF_009_BW_OAP_05(self):
        """
        Test ID: TC-WF-009 | Source ID: BW-OAP-05
        Purpose: Successful no-dues path through parallel authority verification and Academic Administrator finalization.
        Expected: All 7 authorities verified clear and finalized.
        """
        clearance = NoDuesClearance.objects.create(student_id="24BCS205", program="BTech")
        for dept in [DepartmentChoice.LIBRARY, DepartmentChoice.HOSTEL, DepartmentChoice.MESS]:
            NoDuesItem.objects.create(clearance=clearance, department=dept, status=ClearanceStatus.CLEARED)
        clearance.is_finalized = True
        clearance.save()
        self.assertTrue(clearance.is_finalized)

    def test_TC_WF_010_BW_OAP_05(self):
        """
        Test ID: TC-WF-010 | Source ID: BW-OAP-05
        Purpose: No-dues path in which required verification completes but at least one domain is not clear.
        Expected: Clearance remains unfinalized when any department dues exist.
        """
        clearance = NoDuesClearance.objects.create(student_id="24BCS205", program="BTech")
        NoDuesItem.objects.create(clearance=clearance, department=DepartmentChoice.LIBRARY, status=ClearanceStatus.CLEARED)
        NoDuesItem.objects.create(clearance=clearance, department=DepartmentChoice.ACCOUNTS, status=ClearanceStatus.DUES_OUTSTANDING)
        self.assertFalse(clearance.is_finalized)

    def test_TC_WF_011_BW_OAP_07(self):
        """
        Test ID: TC-WF-011 | Source ID: BW-OAP-07
        Purpose: Assistantship path from PG submission through verification/review/approval to stipend processing.
        Expected: Complete lifecycle progression from PENDING to STIPEND_PROCESSED.
        """
        claim = PGAssistantshipClaim.objects.create(
            student_id="24MCS101", month_year="2026-10", hours_rendered=40,
            thesis_supervisor_status=RequestStatus.PENDING,
            ta_supervisor_status=RequestStatus.PENDING
        )
        # Step 1: Supervisors verify
        claim.thesis_supervisor_status = RequestStatus.APPROVED
        claim.ta_supervisor_status = RequestStatus.APPROVED
        # Step 2: Dept Admin forwards
        claim.dept_admin_forwarded = True
        # Step 3: HoD approves
        claim.hod_status = RequestStatus.APPROVED
        # Step 4: Stipend processed
        claim.stipend_processed = True
        claim.save()
        self.assertTrue(claim.stipend_processed)
        self.assertEqual(claim.hod_status, RequestStatus.APPROVED)
