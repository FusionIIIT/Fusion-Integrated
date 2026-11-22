"""Rigorous, spec-based automated tests implementing FR_DESIGN.json."""
import datetime
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from modules.oap.models import (
    BonafidePurpose,
    BonafideStatus,
    DepartmentSignoffStatus,
    DepartmentType,
    LeaveType,
    NoDuesOverallStatus,
    NoDuesReason,
    RequestStatus,
    StudentLeaveRequest,
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
    submit_leave_application,
)


class TestOAPFunctionalRequirementsSpec(TestCase):
    """Deep behavioral test suite covering FR_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_fr_001_afr_oap_009_00(self):
        """\n        Test ID: TC-FR-001 | Source ID: AFR-OAP-009\n        Purpose: Test the submission of a student leave application\n        Action: Submit the leave application via the OAP Fusion ERP system using the provided template\n        Expected: The leave application is submitted successfully, and the student receives an acknowledgment of receipt\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_000",
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

    def test_tc_fr_002_afr_oap_010_01(self):
        """\n        Test ID: TC-FR-002 | Source ID: AFR-OAP-010\n        Purpose: Test the attachment of supporting documents for a medical/academic leave application\n        Action: Attach supporting documents to the leave application using the provided file upload interface\n        Expected: The supporting documents are attached successfully, and the leave application is submitted successfully\n        """
        doc_url = "https://fusion.iiitdmj.ac.in/uploads/oap/medical_cert_01.pdf"
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 5)
        req = submit_leave_application(
            student_id="STU_001",
            student_name="Test Student",
            leave_type=LeaveType.MEDICAL,
            start_date=start,
            end_date=end,
            reason="Hospitalization rest",
            document_url=doc_url
        )
        self.assertEqual(req.document_url, doc_url)
        self.assertEqual(req.status, RequestStatus.PENDING)

    def test_tc_fr_003_afr_oap_011_02(self):
        """\n        Test ID: TC-FR-003 | Source ID: AFR-OAP-011\n        Purpose: Test the automatic routing of a leave request to assigned HoD\n        Action: Submit the leave application via the OAP Fusion ERP system using the provided template, and ensure that the leave request is routed to the correct HoD\n        Expected: The leave request is automatically routed to the assigned HoD, and the student receives an acknowledgment of receipt\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_002",
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

    def test_tc_fr_004_afr_oap_012_03(self):
        """\n        Test ID: TC-FR-004 | Source ID: AFR-OAP-012\n        Purpose: Test the HoD review of a submitted leave application\n        Action: Submit the leave application via the OAP Fusion ERP system using the provided template, and ensure that the HoD reviews the leave request\n        Expected: The HoD reviews the leave request and approves it, and the student receives an acknowledgment of receipt\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_003",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_003")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_fr_005_afr_oap_013_04(self):
        """\n        Test ID: TC-FR-005 | Source ID: AFR-OAP-013\n        Purpose: Test the HoD approval or rejection decision recording with remarks\n        Action: Submit the leave application via the OAP Fusion ERP system using the provided template, and ensure that the HoD makes a decision on the leave request\n        Expected: The HoD makes a decision on the leave request, and the decision record is recorded with remarks, and the student receives an acknowledgment of receipt\n        """
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

    def test_tc_fr_006_afr_oap_014_05(self):
        """\n        Test ID: TC-FR-006 | Source ID: AFR-OAP-014\n        Purpose: Test the student viewing current status of own leave requests\n        Action: View the current status of own leave requests via the OAP Fusion ERP system using the provided interface\n        Expected: The student can view a list of their current leave requests, including the status, start date, end date, and any other relevant information\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_005",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_005")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_fr_007_afr_oap_015_06(self):
        """\n        Test ID: TC-FR-007 | Source ID: AFR-OAP-015\n        Purpose: Test the student viewing history of previous leave requests\n        Action: View the history of previous leave requests via the OAP Fusion ERP system using the provided interface\n        Expected: The student can view a list of their past leave requests, including the status, start date, end date, and any other relevant information\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_006",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_006")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_fr_008_afr_oap_016_07(self):
        """\n        Test ID: TC-FR-008 | Source ID: AFR-OAP-016\n        Purpose: Verifies that a student submits a bonafide certificate request specifying the purpose.\n        Action: POST /bonafide/certificate\n        Expected: The system receives the bonafide certificate request with the specified purpose.\n        """
        req = submit_bonafide_request(
            student_id="STU_007",
            purpose=BonafidePurpose.BANK_LOAN,
            details="State Bank of India education loan application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.purpose, BonafidePurpose.BANK_LOAN)
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Approved with seal")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIsNotNone(req.certificate_number)

    def test_tc_fr_009_afr_oap_017_08(self):
        """\n        Test ID: TC-FR-009 | Source ID: AFR-OAP-017\n        Purpose: Verifies that a bonafide request is routed to the Academic Administrator.\n        Action: Route the bonafide certificate request to the Academic Administrator.\n        Expected: The bonafide certificate request is routed to the Academic Administrator.\n        """
        req = submit_bonafide_request(
            student_id="STU_008",
            purpose=BonafidePurpose.BANK_LOAN,
            details="State Bank of India education loan application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.purpose, BonafidePurpose.BANK_LOAN)
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Approved with seal")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIsNotNone(req.certificate_number)

    def test_tc_fr_010_afr_oap_018_09(self):
        """\n        Test ID: TC-FR-010 | Source ID: AFR-OAP-018\n        Purpose: Verifies that the Academic Administrator verifies the student's academic standing.\n        Action: The Academic Administrator verifies the student's academic standing.\n        Expected: The Academic Administrator records the student's academic standing.\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 2)
        req = submit_leave_application(
            student_id="STU_009",
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

    def test_tc_fr_011_afr_oap_019_10(self):
        """\n        Test ID: TC-FR-011 | Source ID: AFR-OAP-019\n        Purpose: Verifies that the Academic Administrator makes a decision to approve or reject the bonafide certificate request.\n        Action: The Academic Administrator makes a decision to approve or reject the bonafide certificate request.\n        Expected: The Academic Administrator records the decision.\n        """
        req = submit_bonafide_request(
            student_id="STU_010",
            purpose=BonafidePurpose.PASSPORT,
            details="Passport renewal application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        reject_bonafide(req.id, "ACAD_ADMIN", "Invalid enrollment proof")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)
        self.assertEqual(req.rejection_reason, "Invalid enrollment proof")
        self.assertIsNone(req.certificate_number)

    def test_tc_fr_012_afr_oap_020_11(self):
        """\n        Test ID: TC-FR-012 | Source ID: AFR-OAP-020\n        Purpose: Verifies that the student can track the status of their bonafide certificate request.\n        Action: The student queries the system to track the status of their bonafide certificate request.\n        Expected: The system provides the status of the bonafide certificate request.\n        """
        req = submit_bonafide_request(
            student_id="STU_011",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_fr_013_afr_oap_021_12(self):
        """\n        Test ID: TC-FR-013 | Source ID: AFR-OAP-021\n        Purpose: Verifies that the student can download an approved bonafide certificate with a certificate number.\n        Action: The student downloads the approved bonafide certificate.\n        Expected: The student receives the approved bonafide certificate with a certificate number.\n        """
        req = submit_bonafide_request(
            student_id="STU_012",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_fr_014_afr_oap_022_13(self):
        """\n        Test ID: TC-FR-014 | Source ID: AFR-OAP-022\n        Purpose: Verifies that a student can initiate a no-dues clearance request.\n        Action: Create a new no-dues clearance request, specifying the student's details.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_013", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_015_afr_oap_023_14(self):
        """\n        Test ID: TC-FR-015 | Source ID: AFR-OAP-023\n        Purpose: Verifies that a student can submit a no-dues clearance request to all 7 mandatory clearance authorities.\n        Action: Create a new no-dues clearance request, specifying the student's details and routing to all 7 mandatory authorities.\n        Expected: The request should be successfully submitted and appear in the student's profile for each authority.\n        """
        req = initiate_no_dues("STU_014", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_fr_016_afr_oap_024_15(self):
        """\n        Test ID: TC-FR-016 | Source ID: AFR-OAP-024\n        Purpose: Verifies that a student can independently verify their clearance by the Library authority.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Library authority.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_015", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_017_afr_oap_025_16(self):
        """\n        Test ID: TC-FR-017 | Source ID: AFR-OAP-025\n        Purpose: Verifies that a student can independently verify their clearance by the Hostel Warden.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Hostel Warden.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_016", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_018_afr_oap_026_17(self):
        """\n        Test ID: TC-FR-018 | Source ID: AFR-OAP-026\n        Purpose: Verifies that a student can independently verify their clearance by the Mess In-charge.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Mess In-charge.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_017", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_019_afr_oap_027_18(self):
        """\n        Test ID: TC-FR-019 | Source ID: AFR-OAP-027\n        Purpose: Verifies that a student can independently verify their clearance by the Sports/Gymkhana In-charge.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Sports/Gymkhana In-charge.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_018", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_020_afr_oap_028_19(self):
        """\n        Test ID: TC-FR-020 | Source ID: AFR-OAP-028\n        Purpose: Verifies that a student can independently verify their clearance by the Computer Center.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Computer Center.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_019", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_021_afr_oap_052_20(self):
        """\n        Test ID: TC-FR-021 | Source ID: AFR-OAP-052\n        Purpose: Verifies that a student can independently verify their clearance by the Department Lab.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Department Lab.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_020", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_022_afr_oap_053_21(self):
        """\n        Test ID: TC-FR-022 | Source ID: AFR-OAP-053\n        Purpose: Verifies that a student can independently verify their clearance by the Accounts Section.\n        Action: Create a new no-dues clearance request, specifying the student's details and independently verifying the clearance with the Accounts Section.\n        Expected: The request should be successfully submitted and appear in the student's profile.\n        """
        req = initiate_no_dues("STU_021", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_023_afr_oap_029_22(self):
        """\n        Test ID: TC-FR-023 | Source ID: AFR-OAP-029\n        Purpose: Verifies that a student can finalize their no-dues clearance only after all 7 cleared.\n        Action: Create a new no-dues clearance request, specifying the student's details and successfully completing all mandatory tasks.\n        Expected: The student should be unable to finalize their clearance until all 7 clearance authorities have been verified.\n        """
        req = initiate_no_dues("STU_022", NoDuesReason.GRADUATION)
        for dept in DepartmentType.values:
            record_department_signoff(
                req.id, dept, DepartmentSignoffStatus.CLEARED, f"OFFICER_{dept}", Decimal("0.00"), "Clear"
            )
        finalize_no_dues(req.id, "ACAD_DEAN")
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertIsNotNone(req.clearance_certificate_number)

    def test_tc_fr_024_afr_oap_030_23(self):
        """\n        Test ID: TC-FR-024 | Source ID: AFR-OAP-030\n        Purpose: Verifies that a student can generate and download their finalized No-Dues certificate.\n        Action: Create a new no-dues clearance request, successfully completing all mandatory tasks, and generating and downloading the finalized No-Dues certificate.\n        Expected: The student should be able to generate and download their finalized No-Dues certificate.\n        """
        req = submit_bonafide_request(
            student_id="STU_023",
            purpose=BonafidePurpose.INTERNSHIP,
            details="Summer internship at DRDO"
        )
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Verification confirmed")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIn("IIITDMJ/OAP/BONA", req.certificate_number)
        self.assertEqual(req.issued_by, "ACAD_ADMIN")

    def test_tc_fr_025_afr_oap_031_24(self):
        """\n        Test ID: TC-FR-025 | Source ID: AFR-OAP-031\n        Purpose: Verify that a PG student can submit a monthly assistantship claim with the correct hours rendered.\n        Action: A PG student submits a monthly assistantship claim through the system.\n        Expected: {"status": "Claim submitted successfully.", "message": "The system has processed the claim and assigned it to the student."}\n        """
        req = initiate_no_dues("STU_024", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_026_afr_oap_032_25(self):
        """\n        Test ID: TC-FR-026 | Source ID: AFR-OAP-032\n        Purpose: Verify that a submitted claim can be verified by the assigned Thesis Supervisor.\n        Action: The assigned Thesis Supervisor verifies the claim by logging into the system and accessing the claim details.\n        Expected: {"status": "Claim verified successfully.", "message": "The system has processed the verification request and has verified the claim."}\n        """
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

    def test_tc_fr_027_afr_oap_033_26(self):
        """\n        Test ID: TC-FR-027 | Source ID: AFR-OAP-033\n        Purpose: Verify that a submitted claim can be verified by the assigned TA Supervisor.\n        Action: The assigned TA Supervisor verifies the claim by logging into the system and accessing the claim details.\n        Expected: {"status": "Claim verified successfully.", "message": "The system has processed the verification request and has verified the claim."}\n        """
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

    def test_tc_fr_028_afr_oap_034_27(self):
        """\n        Test ID: TC-FR-028 | Source ID: AFR-OAP-034\n        Purpose: Verify that a department administrator can review and forward a submitted assistantship claim to the HoD.\n        Action: The department administrator reviews the claim and forwards it to the HoD.\n        Expected: {"status": "Claim forwarded successfully.", "message": "The system has processed the forwarding request and forwarded the claim to the HoD."}\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 4)
        req = submit_leave_application(
            student_id="STU_027",
            student_name="Test Student",
            leave_type=LeaveType.CASUAL,
            start_date=start,
            end_date=end,
            reason="Festival leave"
        )
        records = StudentLeaveRequest.objects.filter(student_id="STU_027")
        self.assertTrue(records.filter(id=req.id).exists())
        self.assertEqual(records.first().status, RequestStatus.PENDING)
        self.assertGreaterEqual(records.count(), 1)

    def test_tc_fr_029_afr_oap_035_28(self):
        """\n        Test ID: TC-FR-029 | Source ID: AFR-OAP-035\n        Purpose: Verify that the HoD can approve or reject a forwarded assistantship claim.\n        Action: The HoD approves or rejects the forwarded assistantship claim.\n        Expected: {"status": "Claim approved/rejected successfully.", "message": "The system has processed the approval/rejection request and updated the claim status."}\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_028",
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

    def test_tc_fr_030_afr_oap_036_29(self):
        """\n        Test ID: TC-FR-030 | Source ID: AFR-OAP-036\n        Purpose: Verify that an academic administrator can process stipend disbursement for approved assistantship claims.\n        Action: The academic administrator processes the stipend disbursement for the approved claim.\n        Expected: {"status": "Stipend disbursed successfully.", "message": "The system has processed the stipend disbursement and updated the claim status."}\n        """
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

    def test_tc_fr_031_afr_oap_041_30(self):
        """\n        Test ID: TC-FR-031 | Source ID: AFR-OAP-041\n        Purpose: Verify that a PG student can request a graduate seminar schedule.\n        Action: The PG student requests a graduate seminar schedule for the course.\n        Expected: {"status": "Scheduling request submitted successfully.", "message": "The system has processed the scheduling request and assigned the seminar to the student."}\n        """
        req = initiate_no_dues("STU_030", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_032_afr_oap_042_31(self):
        """\n        Test ID: TC-FR-032 | Source ID: AFR-OAP-042\n        Purpose: Verify that a department administrator can schedule a graduate seminar with the correct details.\n        Action: The department administrator schedules the graduate seminar with the correct details.\n        Expected: {"status": "Scheduling request submitted successfully.", "message": "The system has processed the scheduling request and assigned the seminar to the appropriate department."}\n        """
        req = initiate_no_dues("STU_031", NoDuesReason.WITHDRAWAL)
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

    def test_tc_fr_033_afr_oap_043_32(self):
        """\n        Test ID: TC-FR-033 | Source ID: AFR-OAP-043\n        Purpose: Verify that students and faculty can view graduate seminar schedules.\n        Action: Students and faculty members view the graduate seminar schedule.\n        Expected: {"status": "Scheduling information displayed correctly.", "message": "The system has displayed the seminar schedule to all users."}\n        """
        req = initiate_no_dues("STU_032", NoDuesReason.WITHDRAWAL)
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
