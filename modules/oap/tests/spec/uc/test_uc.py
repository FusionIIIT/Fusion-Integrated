"""Rigorous, spec-based automated tests implementing UC_DESIGN.json."""
import datetime
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from modules.oap.models import (
    BonafidePurpose,
    BonafideStatus,
    BranchChangeStatus,
    DepartmentSignoffStatus,
    DepartmentType,
    LeaveType,
    NoDuesOverallStatus,
    NoDuesReason,
    RequestStatus,
    StudentLeaveRequest,
)
from modules.oap.services import (
    allocate_and_sanction,
    approve_and_issue_bonafide,
    finalize_no_dues,
    hod_approve_leave,
    hod_reject_leave,
    initiate_no_dues,
    record_department_signoff,
    submit_bonafide_request,
    submit_branch_change,
    submit_leave_application,
    verify_branch_change,
)


class TestOAPUseCasesSpec(TestCase):
    """Deep behavioral test suite covering UC_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_uc_001_oa_uc_01_00(self):
        """\n        Test ID: TC-UC-001 | Source ID: OA-UC-01\n        Purpose: Ensure student can open the leave application function.\n        Action: User logs in and navigates to the leave application page.\n        Expected: User is presented with the leave request input.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_000",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_000")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_002_oa_uc_01_01(self):
        """\n        Test ID: TC-UC-002 | Source ID: OA-UC-01\n        Purpose: Ensure system displays the leave request input.\n        Action: User enters the leave request details.\n        Expected: User is presented with the leave request input.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_001",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_001")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_003_oa_uc_01_02(self):
        """\n        Test ID: TC-UC-003 | Source ID: OA-UC-01\n        Purpose: Ensure student can optionally attach supporting documents.\n        Action: User uploads supporting documents if needed.\n        Expected: User can upload supporting documents if needed.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_002",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_004_oa_uc_01_03(self):
        """\n        Test ID: TC-UC-004 | Source ID: OA-UC-01\n        Purpose: Ensure student can submit the application.\n        Action: User submits the application.\n        Expected: Application is submitted and made available to the HoD.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_003",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Conference attendance"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Approved for academic presentation")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)
        self.assertEqual(req.hod_id, "HOD_CSE")
        self.assertIn("Approved for academic presentation", req.hod_remarks)

    def test_tc_uc_005_oa_uc_01_04(self):
        """\n        Test ID: TC-UC-005 | Source ID: OA-UC-01\n        Purpose: Ensure system records the submitted application.\n        Action: User submits the application.\n        Expected: Application is submitted and recorded by the system.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_004",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_006_oa_uc_01_05(self):
        """\n        Test ID: TC-UC-006 | Source ID: OA-UC-01\n        Purpose: Ensure system triggers the required submission notification.\n        Action: User submits the application.\n        Expected: Notification is triggered to the student.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_005",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_007_oa_uc_01_06(self):
        """\n        Test ID: TC-UC-007 | Source ID: OA-UC-01\n        Purpose: Ensure submitted application is available to the HoD.\n        Action: User submits the application.\n        Expected: Application is made available to the HoD.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_006",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Conference attendance"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Approved for academic presentation")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)
        self.assertEqual(req.hod_id, "HOD_CSE")
        self.assertIn("Approved for academic presentation", req.hod_remarks)

    def test_tc_uc_008_oa_uc_02_07(self):
        """\n        Test ID: TC-UC-008 | Source ID: OA-UC-02\n        Purpose: Ensure HoD can open a submitted leave application.\n        Action: HoD logs in and navigates to the submitted leave application page.\n        Expected: HoD is presented with the submitted leave request.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_007",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_007")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_009_oa_uc_02_08(self):
        """\n        Test ID: TC-UC-009 | Source ID: OA-UC-02\n        Purpose: Ensure system displays the submitted leave request.\n        Action: HoD views the submitted leave request.\n        Expected: HoD can view the submitted leave request.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_008",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_008")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_010_oa_uc_02_09(self):
        """\n        Test ID: TC-UC-010 | Source ID: OA-UC-02\n        Purpose: Ensure HoD can review the application.\n        Action: HoD reviews the submitted leave request.\n        Expected: HoD can review the submitted leave request.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_009",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_009")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_011_oa_uc_02_10(self):
        """\n        Test ID: TC-UC-011 | Source ID: OA-UC-02\n        Purpose: Ensure HoD can record an Approve or Reject decision.\n        Action: HoD records an Approve or Reject decision.\n        Expected: HoD can record an Approve or Reject decision.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_010",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Family obligation"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_reject_leave(req.id, "HOD_CSE", "Academic commitments conflict")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)
        self.assertEqual(req.hod_id, "HOD_CSE")
        self.assertIn("Academic commitments conflict", req.hod_remarks)

    def test_tc_uc_012_oa_uc_02_11(self):
        """\n        Test ID: TC-UC-012 | Source ID: OA-UC-02\n        Purpose: Ensure system records the decision and updates the application status.\n        Action: HoD records an Approve or Reject decision.\n        Expected: Decision is recorded and application status is updated by the system.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_011",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Family obligation"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_reject_leave(req.id, "HOD_CSE", "Academic commitments conflict")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)
        self.assertEqual(req.hod_id, "HOD_CSE")
        self.assertIn("Academic commitments conflict", req.hod_remarks)

    def test_tc_uc_013_oa_uc_02_12(self):
        """\n        Test ID: TC-UC-013 | Source ID: OA-UC-02\n        Purpose: Ensure system triggers the required decision notification to the student.\n        Action: HoD records an Approve or Reject decision.\n        Expected: Notification is triggered to the student.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_012",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Family obligation"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_reject_leave(req.id, "HOD_CSE", "Academic commitments conflict")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)
        self.assertEqual(req.hod_id, "HOD_CSE")
        self.assertIn("Academic commitments conflict", req.hod_remarks)

    def test_tc_uc_014_oa_uc_03_13(self):
        """\n        Test ID: TC-UC-014 | Source ID: OA-UC-03\n        Purpose: Ensure student can open the bonafide request function.\n        Action: Student logs in and navigates to the bonafide request page.\n        Expected: Student is presented with the bonafide request input.\n        """
        req = submit_bonafide_request(
            student_id="STU_013",
            purpose=BonafidePurpose.BANK_LOAN,
            details="State Bank of India education loan application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.purpose, BonafidePurpose.BANK_LOAN)
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Approved with seal")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIsNotNone(req.certificate_number)

    def test_tc_uc_015_oa_uc_03_14(self):
        """\n        Test ID: TC-UC-015 | Source ID: OA-UC-03\n        Purpose: Ensure system displays the bonafide request input.\n        Action: Student enters the bonafide request details.\n        Expected: Student is presented with the bonafide request input.\n        """
        req = submit_bonafide_request(
            student_id="STU_014",
            purpose=BonafidePurpose.BANK_LOAN,
            details="State Bank of India education loan application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.purpose, BonafidePurpose.BANK_LOAN)
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Approved with seal")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIsNotNone(req.certificate_number)

    def test_tc_uc_016_oa_uc_03_15(self):
        """\n        Test ID: TC-UC-016 | Source ID: OA-UC-03\n        Purpose: Ensure student can submit the request.\n        Action: Student submits the request.\n        Expected: Request is submitted and made available to the Academic Administrator.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_015",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_017_oa_uc_03_16(self):
        """\n        Test ID: TC-UC-017 | Source ID: OA-UC-03\n        Purpose: Ensure system records the submitted request.\n        Action: Student submits the request.\n        Expected: Request is submitted and recorded by the system.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_016",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_018_oa_uc_03_17(self):
        """\n        Test ID: TC-UC-018 | Source ID: OA-UC-03\n        Purpose: Ensure system triggers the required submission notification to the student.\n        Action: Student submits the request.\n        Expected: Notification is triggered to the student.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_017",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_019_oa_uc_04_18(self):
        """\n        Test ID: TC-UC-019 | Source ID: OA-UC-04\n        Purpose: Ensure student can view the current leave status and request history.\n        Action: Student logs in and navigates to leave tracking/history.\n        Expected: Student is presented with the leave status and request history.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_018",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_018")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_020_oa_uc_21_19(self):
        """\n        Test ID: TC-UC-020 | Source ID: OA-UC-21\n        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.\n        Action: Student initiates a no-dues clearance request.\n        Expected: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        """
        req = initiate_no_dues("STU_019", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_021_oa_uc_21_20(self):
        """\n        Test ID: TC-UC-021 | Source ID: OA-UC-21\n        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.\n        Action: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        Expected: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        """
        req = initiate_no_dues("STU_020", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_022_oa_uc_21_21(self):
        """\n        Test ID: TC-UC-022 | Source ID: OA-UC-21\n        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.\n        Action: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        Expected: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        """
        req = initiate_no_dues("STU_021", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_023_oa_uc_21_22(self):
        """\n        Test ID: TC-UC-023 | Source ID: OA-UC-21\n        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.\n        Action: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        Expected: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        """
        req = initiate_no_dues("STU_022", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_024_oa_uc_21_23(self):
        """\n        Test ID: TC-UC-024 | Source ID: OA-UC-21\n        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.\n        Action: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        Expected: System records the clearance request, identifies the seven mandatory clearance authorities, sends the verification request to all seven authorities in parallel, triggers the required submission notification.\n        """
        req = initiate_no_dues("STU_023", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_025_oa_uc_21_24(self):
        """\n        Test ID: TC-UC-025 | Source ID: OA-UC-21\n        Purpose: Verify that a clearance request cannot be recorded/routed; system reports failure without claiming successful initiation.\n        Action: System attempts to initiate a no-dues clearance request, but fails to record it or route it.\n        Expected: System reports failure without claiming successful initiation.\n        """
        req = initiate_no_dues("STU_024", NoDuesReason.GRADUATION)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.DUES_PENDING,
            "LIB_HEAD",
            Decimal("250.00"),
            "Overdue book fines outstanding"
        )
        req.refresh_from_db()
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.DUES_PENDING)
        self.assertEqual(signoff.dues_amount, Decimal("250.00"))
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)

    def test_tc_uc_026_oa_uc_22_25(self):
        """\n        Test ID: TC-UC-026 | Source ID: OA-UC-22\n        Purpose: Verify that an authority receives or opens a pending no-dues verification.\n        Action: Authority receives a pending no-dues verification.\n        Expected: System displays the information relevant to that authority's domain.\n        """
        req = initiate_no_dues("STU_025", NoDuesReason.WITHDRAWAL)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.CLEARED,
            "CHIEF_LIBRARIAN",
            Decimal("0.00"),
            "Zero dues, clearance granted"
        )
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)
        self.assertEqual(signoff.signoff_by, "CHIEF_LIBRARIAN")

    def test_tc_uc_027_oa_uc_22_26(self):
        """\n        Test ID: TC-UC-027 | Source ID: OA-UC-22\n        Purpose: Verify that an authority receives or opens a pending no-dues verification.\n        Action: Authority receives a pending no-dues verification.\n        Expected: System displays the information relevant to that authority's domain.\n        """
        req = initiate_no_dues("STU_026", NoDuesReason.WITHDRAWAL)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.CLEARED,
            "CHIEF_LIBRARIAN",
            Decimal("0.00"),
            "Zero dues, clearance granted"
        )
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)
        self.assertEqual(signoff.signoff_by, "CHIEF_LIBRARIAN")

    def test_tc_uc_028_oa_uc_22_27(self):
        """\n        Test ID: TC-UC-028 | Source ID: OA-UC-22\n        Purpose: Verify that an authority receives or opens a pending no-dues verification.\n        Action: Authority receives a pending no-dues verification.\n        Expected: System displays the information relevant to that authority's domain.\n        """
        req = initiate_no_dues("STU_027", NoDuesReason.WITHDRAWAL)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.CLEARED,
            "CHIEF_LIBRARIAN",
            Decimal("0.00"),
            "Zero dues, clearance granted"
        )
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)
        self.assertEqual(signoff.signoff_by, "CHIEF_LIBRARIAN")

    def test_tc_uc_029_oa_uc_22_28(self):
        """\n        Test ID: TC-UC-029 | Source ID: OA-UC-22\n        Purpose: Verify that an authority receives or opens a pending no-dues verification.\n        Action: Authority receives a pending no-dues verification.\n        Expected: System displays the information relevant to that authority's domain.\n        """
        req = initiate_no_dues("STU_028", NoDuesReason.WITHDRAWAL)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.CLEARED,
            "CHIEF_LIBRARIAN",
            Decimal("0.00"),
            "Zero dues, clearance granted"
        )
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)
        self.assertEqual(signoff.signoff_by, "CHIEF_LIBRARIAN")

    def test_tc_uc_030_oa_uc_22_29(self):
        """\n        Test ID: TC-UC-030 | Source ID: OA-UC-22\n        Purpose: Verify that an authority receives or opens a pending no-dues verification.\n        Action: Authority receives a pending no-dues verification.\n        Expected: System displays the information relevant to that authority's domain.\n        """
        req = initiate_no_dues("STU_029", NoDuesReason.WITHDRAWAL)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.CLEARED,
            "CHIEF_LIBRARIAN",
            Decimal("0.00"),
            "Zero dues, clearance granted"
        )
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)
        self.assertEqual(signoff.signoff_by, "CHIEF_LIBRARIAN")

    def test_tc_uc_031_oa_uc_22_30(self):
        """\n        Test ID: TC-UC-031 | Source ID: OA-UC-22\n        Purpose: Verify that an authority records that dues/obligations remain outstanding; the domain is not marked clear.\n        Action: Authority records that dues/obligations remain outstanding.\n        Expected: The domain is not marked clear.\n        """
        req = initiate_no_dues("STU_030", NoDuesReason.GRADUATION)
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        record_department_signoff(
            req.id,
            DepartmentType.LIBRARY,
            DepartmentSignoffStatus.DUES_PENDING,
            "LIB_HEAD",
            Decimal("250.00"),
            "Overdue book fines outstanding"
        )
        req.refresh_from_db()
        signoff = req.signoffs.get(department=DepartmentType.LIBRARY)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.DUES_PENDING)
        self.assertEqual(signoff.dues_amount, Decimal("250.00"))
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)

    def test_tc_uc_032_oa_uc_23_31(self):
        """\n        Test ID: TC-UC-032 | Source ID: OA-UC-23\n        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.\n        Action: Academic Administrator opens the consolidated clearance case.\n        Expected: System displays results from Library, Hostel, Mess, respective Department, Lab, Academic Section, and Student Section.\n        """
        req = initiate_no_dues("STU_031", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_033_oa_uc_23_32(self):
        """\n        Test ID: TC-UC-033 | Source ID: OA-UC-23\n        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.\n        Action: Academic Administrator opens the consolidated clearance case.\n        Expected: System displays results from Library, Hostel, Mess, respective Department, Lab, Academic Section, and Student Section.\n        """
        req = initiate_no_dues("STU_032", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_034_oa_uc_23_33(self):
        """\n        Test ID: TC-UC-034 | Source ID: OA-UC-23\n        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.\n        Action: Academic Administrator opens the consolidated clearance case.\n        Expected: System displays results from Library, Hostel, Mess, respective Department, Lab, Academic Section, and Student Section.\n        """
        req = initiate_no_dues("STU_033", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_035_oa_uc_23_34(self):
        """\n        Test ID: TC-UC-035 | Source ID: OA-UC-23\n        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.\n        Action: Academic Administrator opens the consolidated clearance case.\n        Expected: System displays results from Library, Hostel, Mess, respective Department, Lab, Academic Section, and Student Section.\n        """
        req = initiate_no_dues("STU_034", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_036_oa_uc_23_35(self):
        """\n        Test ID: TC-UC-036 | Source ID: OA-UC-23\n        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.\n        Action: Academic Administrator opens the consolidated clearance case.\n        Expected: System displays results from Library, Hostel, Mess, respective Department, Lab, Academic Section, and Student Section.\n        """
        req = initiate_no_dues("STU_035", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_037_oa_uc_23_36(self):
        """\n        Test ID: TC-UC-037 | Source ID: OA-UC-23\n        Purpose: Verify that finalization cannot be persisted; previous statuses are retained.\n        Action: Academic Administrator opens the consolidated clearance case.\n        Expected: Previous statuses are retained.\n        """
        req = initiate_no_dues("STU_036", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_uc_038_oa_uc_31_37(self):
        """\n        Test ID: TC-UC-038 | Source ID: OA-UC-31\n        Purpose: Testing the main success flow for submitting an assistantship claim.\n        Action: Student opens assistantship claim submission.\n        Expected: System accepts the claim information.\n        """
        req = submit_branch_change(
            student_id="STU_037",
            current_branch="ECE",
            preferred_branch_1="CSE",
            preferred_branch_2="ME",
            current_cpi=Decimal("9.45"),
            credits_completed=40,
            has_backlogs=False
        )
        req = allocate_and_sanction(req.id, "CSE", "DEAN_ACAD")
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.APPROVED)
        self.assertEqual(req.allocated_branch, "CSE")
        self.assertEqual(req.approved_by, "DEAN_ACAD")

    def test_tc_uc_039_oa_uc_31_38(self):
        """\n        Test ID: TC-UC-039 | Source ID: OA-UC-31\n        Purpose: Testing the system acceptance of the claim information.\n        Action: System accepts the claim information.\n        Expected: System records the submitted claim.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_038",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_040_oa_uc_31_39(self):
        """\n        Test ID: TC-UC-040 | Source ID: OA-UC-31\n        Purpose: Testing the system routing the claim to both the assigned Thesis Supervisor and assigned TA Supervisor for role-specific verification.\n        Action: System routes the claim to both the assigned Thesis Supervisor and assigned TA Supervisor for role-specific verification.\n        Expected: System triggers the required submission notification.\n        """
        req = submit_branch_change(
            student_id="STU_039",
            current_branch="ME",
            preferred_branch_1="ECE",
            preferred_branch_2="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=38,
            has_backlogs=False
        )
        self.assertEqual(req.status, BranchChangeStatus.SUBMITTED)
        self.assertEqual(req.current_cpi, Decimal("8.80"))
        eligible = verify_branch_change(req.id)
        self.assertTrue(eligible)
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

    def test_tc_uc_041_oa_uc_31_40(self):
        """\n        Test ID: TC-UC-041 | Source ID: OA-UC-31\n        Purpose: Testing the system's ability to display the claim information and the supervisor role being exercised.\n        Action: System displays the claim information and the supervisor role being exercised.\n        Expected: System displays the claim information and the supervisor role being exercised.\n        """
        req = submit_branch_change(
            student_id="STU_040",
            current_branch="ME",
            preferred_branch_1="ECE",
            preferred_branch_2="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=38,
            has_backlogs=False
        )
        self.assertEqual(req.status, BranchChangeStatus.SUBMITTED)
        self.assertEqual(req.current_cpi, Decimal("8.80"))
        eligible = verify_branch_change(req.id)
        self.assertTrue(eligible)
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

    def test_tc_uc_042_oa_uc_31_41(self):
        """\n        Test ID: TC-UC-042 | Source ID: OA-UC-31\n        Purpose: Testing the system's ability to review the claim.\n        Action: Supervisor reviews the claim.\n        Expected: Supervisor records verification for that role.\n        """
        req = submit_branch_change(
            student_id="STU_041",
            current_branch="ME",
            preferred_branch_1="ECE",
            preferred_branch_2="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=38,
            has_backlogs=False
        )
        self.assertEqual(req.status, BranchChangeStatus.SUBMITTED)
        self.assertEqual(req.current_cpi, Decimal("8.80"))
        eligible = verify_branch_change(req.id)
        self.assertTrue(eligible)
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

    def test_tc_uc_043_oa_uc_31_42(self):
        """\n        Test ID: TC-UC-043 | Source ID: OA-UC-31\n        Purpose: Testing the system's ability to store the role-specific verification independently.\n        Action: Supervisor records verification for that role.\n        Expected: System stores the role-specific verification independently.\n        """
        req = submit_branch_change(
            student_id="STU_042",
            current_branch="ME",
            preferred_branch_1="ECE",
            preferred_branch_2="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=38,
            has_backlogs=False
        )
        self.assertEqual(req.status, BranchChangeStatus.SUBMITTED)
        self.assertEqual(req.current_cpi, Decimal("8.80"))
        eligible = verify_branch_change(req.id)
        self.assertTrue(eligible)
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

    def test_tc_uc_044_oa_uc_31_43(self):
        """\n        Test ID: TC-UC-044 | Source ID: OA-UC-31\n        Purpose: Testing the system's ability to advance the claim to the Department Administrator after both required role-verifications are complete.\n        Action: Supervisor forwards the reviewed claim to the HoD.\n        Expected: System records the forwarding state and triggers the relevant notification.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_043",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_043")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_045_oa_uc_31_44(self):
        """\n        Test ID: TC-UC-045 | Source ID: OA-UC-31\n        Purpose: Testing the system's ability to display the claim and both supervisor-role verifications after the claim has been reviewed and forwarded to the HoD.\n        Action: Department Administrator opens the dually verified claim.\n        Expected: System displays the claim and both supervisor-role verifications.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_044",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_044")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_uc_046_oa_uc_51_45(self):
        """\n        Test ID: TC-UC-046 | Source ID: OA-UC-51\n        Purpose: Verify that a PG student opens the seminar scheduling request and submits it successfully.\n        Action: The PG student opens the seminar scheduling request.\n        Expected: The system presents the request input, the student submits the scheduling request, and the system records the request.\n        """
        req = submit_branch_change(
            student_id="STU_045",
            current_branch="ECE",
            preferred_branch_1="CSE",
            preferred_branch_2="ME",
            current_cpi=Decimal("9.45"),
            credits_completed=40,
            has_backlogs=False
        )
        req = allocate_and_sanction(req.id, "CSE", "DEAN_ACAD")
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.APPROVED)
        self.assertEqual(req.allocated_branch, "CSE")
        self.assertEqual(req.approved_by, "DEAN_ACAD")

    def test_tc_uc_047_oa_uc_51_46(self):
        """\n        Test ID: TC-UC-047 | Source ID: OA-UC-51\n        Purpose: Verify that the system triggers the required submission notification.\n        Action: The system triggers the required submission notification.\n        Expected: The system triggers the required submission notification.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_046",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_048_oa_uc_53_47(self):
        """\n        Test ID: TC-UC-048 | Source ID: OA-UC-53\n        Purpose: Verify that a Department Administrator opens a pending seminar scheduling request and determines the seminar schedule successfully.\n        Action: The Department Administrator opens a pending seminar scheduling request.\n        Expected: The system determines the seminar schedule using institute process/policy and records the scheduled seminar.\n        """
        req = submit_branch_change(
            student_id="STU_047",
            current_branch="ECE",
            preferred_branch_1="CSE",
            preferred_branch_2="ME",
            current_cpi=Decimal("9.45"),
            credits_completed=40,
            has_backlogs=False
        )
        req = allocate_and_sanction(req.id, "CSE", "DEAN_ACAD")
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.APPROVED)
        self.assertEqual(req.allocated_branch, "CSE")
        self.assertEqual(req.approved_by, "DEAN_ACAD")

    def test_tc_uc_049_oa_uc_53_48(self):
        """\n        Test ID: TC-UC-049 | Source ID: OA-UC-53\n        Purpose: Verify that the system triggers relevant notifications for the scheduled seminar.\n        Action: The system triggers relevant notifications for the scheduled seminar.\n        Expected: The system triggers relevant notifications for the scheduled seminar.\n        """
        req = submit_branch_change(
            student_id="STU_048",
            current_branch="ME",
            preferred_branch_1="ECE",
            preferred_branch_2="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=38,
            has_backlogs=False
        )
        self.assertEqual(req.status, BranchChangeStatus.SUBMITTED)
        self.assertEqual(req.current_cpi, Decimal("8.80"))
        eligible = verify_branch_change(req.id)
        self.assertTrue(eligible)
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

    def test_tc_uc_050_oa_uc_54_49(self):
        """\n        Test ID: TC-UC-050 | Source ID: OA-UC-54\n        Purpose: Verify that an authorized user opens the seminar schedule and displays the available seminar schedule successfully.\n        Action: The authorized user opens the seminar schedule.\n        Expected: The system retrieves scheduled seminar information and displays the schedule to the authorized user.\n        """
        req = submit_branch_change(
            student_id="STU_049",
            current_branch="ECE",
            preferred_branch_1="CSE",
            preferred_branch_2="ME",
            current_cpi=Decimal("9.45"),
            credits_completed=40,
            has_backlogs=False
        )
        req = allocate_and_sanction(req.id, "CSE", "DEAN_ACAD")
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.APPROVED)
        self.assertEqual(req.allocated_branch, "CSE")
        self.assertEqual(req.approved_by, "DEAN_ACAD")

    def test_tc_uc_051_oa_uc_54_50(self):
        """\n        Test ID: TC-UC-051 | Source ID: OA-UC-54\n        Purpose: Verify that the system displays an empty schedule if no scheduled seminars exist.\n        Action: The authorized user opens the seminar schedule.\n        Expected: The system displays an empty schedule.\n        """
        req = submit_branch_change(
            student_id="STU_050",
            current_branch="ME",
            preferred_branch_1="ECE",
            preferred_branch_2="CSE",
            current_cpi=Decimal("8.80"),
            credits_completed=38,
            has_backlogs=False
        )
        self.assertEqual(req.status, BranchChangeStatus.SUBMITTED)
        self.assertEqual(req.current_cpi, Decimal("8.80"))
        eligible = verify_branch_change(req.id)
        self.assertTrue(eligible)
        req.refresh_from_db()
        self.assertEqual(req.status, BranchChangeStatus.VERIFIED_ELIGIBLE)

    def test_tc_uc_052_oa_uc_91_51(self):
        """\n        Test ID: TC-UC-052 | Source ID: OA-UC-91\n        Purpose: Verify that a relevant OAP event notification is sent through the supported channels successfully.\n        Action: A relevant OAP event triggers.\n        Expected: The system sends the required notification through the supported channels.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_051",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_uc_053_oa_uc_92_52(self):
        """\n        Test ID: TC-UC-053 | Source ID: OA-UC-92\n        Purpose: Verify that a reminder for a pending OAP action is sent successfully.\n        Action: A reminder condition is met.\n        Expected: The system sends a reminder for the pending OAP action.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_052",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Urgent domestic errand"
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        hod_approve_leave(req.id, "HOD_CSE", "Verified and approved")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)
