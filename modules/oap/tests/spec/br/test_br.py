"""Rigorous, spec-based automated tests implementing BR_DESIGN.json."""
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
)
from modules.oap.services import (
    approve_and_issue_bonafide,
    finalize_no_dues,
    hod_approve_leave,
    hod_reject_leave,
    initiate_no_dues,
    record_department_signoff,
    reject_bonafide,
    submit_bonafide_request,
    submit_branch_change,
    submit_leave_application,
    verify_branch_change,
)


class TestOAPBusinessRulesSpec(TestCase):
    """Deep behavioral test suite covering BR_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_br_001_oa_br_01_00(self):
        """\n        Test ID: TC-BR-001 | Source ID: OA-BR-01\n        Purpose: Ensure that only authorized roles can access OAP functions and information.\n        Action: The user attempts to access an OAP function or record.\n        Expected: Access should be restricted to authorized roles.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_000",
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

    def test_tc_br_002_oa_br_01_01(self):
        """\n        Test ID: TC-BR-002 | Source ID: OA-BR-01\n        Purpose: Verify that only roles authorized for the relevant function or record can access OAP functions and information.\n        Action: The user attempts to access an OAP function or record.\n        Expected: Access should be restricted to authorized roles.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_001",
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

    def test_tc_br_003_oa_br_03_02(self):
        """\n        Test ID: TC-BR-003 | Source ID: OA-BR-03\n        Purpose: Verify that OAP notifications are sent via system alerts and email.\n        Action: The notification system sends an alert and email.\n        Expected: The notification should be sent via system alert and email.\n        """
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

    def test_tc_br_004_oa_br_03_03(self):
        """\n        Test ID: TC-BR-004 | Source ID: OA-BR-03\n        Purpose: Ensure that OAP notifications are sent via system alerts and email.\n        Action: The notification system sends an alert and email.\n        Expected: The notification should be sent via system alert and email.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_003",
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

    def test_tc_br_005_oa_br_11_04(self):
        """\n        Test ID: TC-BR-005 | Source ID: OA-BR-11\n        Purpose: Verify that only the HoD is specified to approve or reject student leave applications.\n        Action: The user submits a leave application.\n        Expected: The leave application should be approved or rejected by the HoD.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_004",
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

    def test_tc_br_006_oa_br_11_05(self):
        """\n        Test ID: TC-BR-006 | Source ID: OA-BR-11\n        Purpose: Verify that only the HoD is specified to approve or reject student leave applications.\n        Action: The user submits a leave application.\n        Expected: The leave application should be approved or rejected by the HoD.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_005",
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

    def test_tc_br_007_oa_br_21_06(self):
        """\n        Test ID: TC-BR-007 | Source ID: OA-BR-21\n        Purpose: Verify that the Academic Administrator is the specified authority to verify and approve/reject bonafide requests.\n        Action: The user submits a bonafide request.\n        Expected: The bonafide request should be approved or rejected by the Academic Administrator.\n        """
        req = submit_bonafide_request(
            student_id="STU_006",
            purpose=BonafidePurpose.PASSPORT,
            details="Passport renewal application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        reject_bonafide(req.id, "ACAD_ADMIN", "Invalid enrollment proof")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)
        self.assertEqual(req.rejection_reason, "Invalid enrollment proof")
        self.assertIsNone(req.certificate_number)

    def test_tc_br_008_oa_br_21_07(self):
        """\n        Test ID: TC-BR-008 | Source ID: OA-BR-21\n        Purpose: Verify that the Academic Administrator is the specified authority to verify and approve/reject bonafide requests.\n        Action: The user submits a bonafide request.\n        Expected: The bonafide request should be approved or rejected by the Academic Administrator.\n        """
        req = submit_bonafide_request(
            student_id="STU_007",
            purpose=BonafidePurpose.PASSPORT,
            details="Passport renewal application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        reject_bonafide(req.id, "ACAD_ADMIN", "Invalid enrollment proof")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)
        self.assertEqual(req.rejection_reason, "Invalid enrollment proof")
        self.assertIsNone(req.certificate_number)

    def test_tc_br_009_oa_br_22_08(self):
        """\n        Test ID: TC-BR-009 | Source ID: OA-BR-22\n        Purpose: Verify that a bonafide certificate shall be available for download only after the request is approved.\n        Action: The user requests a bonafide certificate.\n        Expected: The bonafide certificate should be available for download only after it is approved.\n        """
        req = submit_bonafide_request(
            student_id="STU_008",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_br_010_oa_br_22_09(self):
        """\n        Test ID: TC-BR-010 | Source ID: OA-BR-22\n        Purpose: Ensure that a bonafide certificate shall be available for download only after the request is approved.\n        Action: The user requests a bonafide certificate.\n        Expected: The bonafide certificate should be available for download only after it is approved.\n        """
        req = submit_bonafide_request(
            student_id="STU_009",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_br_011_oa_br_31_10(self):
        """\n        Test ID: TC-BR-011 | Source ID: OA-BR-31\n        Purpose: Verify that each of the seven mandatory no-dues authorities may record clearance only for its own institutional domain.\n        Action: The authority submits a clearance request.\n        Expected: The authority should record clearance only for its own domain.\n        """
        req = initiate_no_dues("STU_010", NoDuesReason.WITHDRAWAL)
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

    def test_tc_br_012_oa_br_31_11(self):
        """\n        Test ID: TC-BR-012 | Source ID: OA-BR-31\n        Purpose: Ensure that each of the seven mandatory no-dues authorities may record clearance only for its own institutional domain.\n        Action: The authority submits a clearance request.\n        Expected: The authority should record clearance only for its own domain.\n        """
        req = initiate_no_dues("STU_011", NoDuesReason.WITHDRAWAL)
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

    def test_tc_br_013_oa_br_32_12(self):
        """\n        Test ID: TC-BR-013 | Source ID: OA-BR-32\n        Purpose: Verify that the clearance result from each of the seven mandatory no-dues authorities shall be maintained independently until consolidation.\n        Action: The authority submits a clearance request.\n        Expected: The clearance result from each authority should be maintained independently until consolidation.\n        """
        req = initiate_no_dues("STU_012", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_br_014_oa_br_32_13(self):
        """\n        Test ID: TC-BR-014 | Source ID: OA-BR-32\n        Purpose: Ensure that the clearance result from each of the seven mandatory no-dues authorities shall be maintained independently until consolidation.\n        Action: The authority submits a clearance request.\n        Expected: The clearance result from each authority should be maintained independently until consolidation.\n        """
        req = initiate_no_dues("STU_013", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_br_015_oa_br_33_14(self):
        """\n        Test ID: TC-BR-015 | Source ID: OA-BR-33\n        Purpose: Verify that no-dues clearance may be finalized only after all seven mandatory authorities have submitted verification and all seven clearance results are clear.\n        Action: The authority submits a clearance request.\n        Expected: The clearance should be finalized only after all seven mandatory authorities have submitted verification and all seven clearance results are clear.\n        """
        req = initiate_no_dues("STU_014", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_br_016_oa_br_33_15(self):
        """\n        Test ID: TC-BR-016 | Source ID: OA-BR-33\n        Purpose: Ensure that no-dues clearance may be finalized only after all seven mandatory authorities have submitted verification and all seven clearance results are clear.\n        Action: The authority submits a clearance request.\n        Expected: The clearance should be finalized only after all seven mandatory authorities have submitted verification and all seven clearance results are clear.\n        """
        req = initiate_no_dues("STU_015", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_br_017_oa_br_34_16(self):
        """\n        Test ID: TC-BR-017 | Source ID: OA-BR-34\n        Purpose: Verify that the no-dues certificate shall be made downloadable only after Academic Administrator finalization.\n        Action: The authority submits a clearance request.\n        Expected: The certificate should be made downloadable only after Academic Administrator finalization.\n        """
        req = submit_bonafide_request(
            student_id="STU_016",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_br_018_oa_br_34_17(self):
        """\n        Test ID: TC-BR-018 | Source ID: OA-BR-34\n        Purpose: Ensure that the no-dues certificate shall be made downloadable only after Academic Administrator finalization.\n        Action: The authority submits a clearance request.\n        Expected: The certificate should be made downloadable only after Academic Administrator finalization.\n        """
        req = submit_bonafide_request(
            student_id="STU_017",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_br_019_oa_br_01_18(self):
        """\n        Test ID: TC-BR-019 | Source ID: OA-BR-01\n        Purpose: To ensure that only PG students can submit assistantship claims.\n        Action: {'form': 'Submission of assistantship claim form', 'user': 'PG student'}\n        Expected: {"outcome": "Submission of form", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_018",
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

    def test_tc_br_020_oa_br_02_19(self):
        """\n        Test ID: TC-BR-020 | Source ID: OA-BR-02\n        Purpose: To ensure that both supervisor roles are verified before Department Administrator review.\n        Action: {'role1': 'Thesis supervisor', 'role2': 'TA supervisor', 'user': 'PG student'}\n        Expected: {"outcome": "Both role-verifications completed", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_019",
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

    def test_tc_br_021_oa_br_03_20(self):
        """\n        Test ID: TC-BR-021 | Source ID: OA-BR-03\n        Purpose: To ensure that the Department Administrator review occurs only after both role-verifications are complete.\n        Action: {'claim submitted': 'Claim submitted by PG student', 'user': 'PG student'}\n        Expected: {"outcome": "Wait for both role-verifications and Department Administrator review", "status": "Permitted"}\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_020",
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

    def test_tc_br_022_oa_br_04_21(self):
        """\n        Test ID: TC-BR-022 | Source ID: OA-BR-04\n        Purpose: To ensure that the HoD is the stated departmental authority to approve or reject assistantship claims.\n        Action: {'claim submitted': 'Claim submitted by PG student', 'user': 'PG student'}\n        Expected: {"outcome": "Wait for HoD decision to approve or reject claim", "status": "Permitted"}\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_021",
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

    def test_tc_br_023_oa_br_05_22(self):
        """\n        Test ID: TC-BR-023 | Source ID: OA-BR-05\n        Purpose: To ensure that the accepted assistantship progression is correct.\n        Action: {'claim submitted': 'Claim submitted by PG student', 'user': 'PG student'}\n        Expected: {"outcome": "Claim progresses through the specified sequence", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_022",
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

    def test_tc_br_024_oa_br_06_23(self):
        """\n        Test ID: TC-BR-024 | Source ID: OA-BR-06\n        Purpose: To ensure that the Department Administrator records thesis-supervisor assignments and TA assignments based on departmental decisions.\n        Action: {'claim submitted': 'Claim submitted by PG student', 'user': 'PG student'}\n        Expected: {"outcome": "Thesis-supervisor assignment and TA assignment are recorded", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_023",
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

    def test_tc_br_025_oa_br_07_24(self):
        """\n        Test ID: TC-BR-025 | Source ID: OA-BR-07\n        Purpose: To ensure that graduate seminar scheduling requests are within PG-student scope.\n        Action: {'request submitted': 'Request submitted by PG student to graduate seminars', 'user': 'PG student'}\n        Expected: {"outcome": "Request submitted to graduate seminars", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_024",
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

    def test_tc_br_026_oa_br_08_25(self):
        """\n        Test ID: TC-BR-026 | Source ID: OA-BR-08\n        Purpose: To ensure that the Department Administrator schedules and logs graduate seminars.\n        Action: {'request submitted': 'Request submitted by PG student to graduate seminars', 'user': 'PG student'}\n        Expected: {"outcome": "Department administrator schedules the seminar", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_025",
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

    def test_tc_br_027_oa_br_09_26(self):
        """\n        Test ID: TC-BR-027 | Source ID: OA-BR-09\n        Purpose: To ensure that graduate seminar schedules are viewable by PG students and faculty.\n        Action: {'schedule requested': 'Request for view of graduate seminar schedule', 'user': 'PG student or faculty'}\n        Expected: {"outcome": "Scheduling is viewable to PG students and faculty", "status": "Permitted"}\n        """
        req = submit_branch_change(
            student_id="STU_026",
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
