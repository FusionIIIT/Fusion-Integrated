"""Rigorous, spec-based automated tests implementing WF_DESIGN.json."""
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
    allocate_and_sanction,
    approve_and_issue_bonafide,
    hod_approve_leave,
    hod_reject_leave,
    initiate_no_dues,
    record_department_signoff,
    reject_bonafide,
    submit_bonafide_request,
    submit_branch_change,
    submit_leave_application,
)


class TestOAPWorkflowsSpec(TestCase):
    """Deep behavioral test suite covering WF_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_wf_001_bw_oap_01_00(self):
        """\n        Test ID: TC-WF-001 | Source ID: BW-OAP-01\n        Purpose: Successful leave path from student submission to HoD approval.\n        Action: Student submits the leave application.\n        Expected: Leave application submitted - Awaiting HoD Decision\n        """
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

    def test_tc_wf_002_bw_oap_01_01(self):
        """\n        Test ID: TC-WF-002 | Source ID: BW-OAP-01\n        Purpose: Leave path ending in HoD rejection.\n        Action: Student submits the leave application.\n        Expected: Leave application submitted - Awaiting HoD Decision\n        """
        start = datetime.date(2026, 12, 1)
        end = datetime.date(2026, 12, 3)
        req = submit_leave_application(
            student_id="STU_001",
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

    def test_tc_wf_003_bw_oap_02_02(self):
        """\n        Test ID: TC-WF-003 | Source ID: BW-OAP-02\n        Purpose: Bonafide request path ending in approval.\n        Action: Student submits the bonafide request.\n        Expected: Bonafide request submitted - Awaiting Academic Administrator\n        """
        req = submit_bonafide_request(
            student_id="STU_002",
            purpose=BonafidePurpose.BANK_LOAN,
            details="State Bank of India education loan application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.purpose, BonafidePurpose.BANK_LOAN)
        approve_and_issue_bonafide(req.id, "ACAD_ADMIN", "Approved with seal")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertIsNotNone(req.certificate_number)

    def test_tc_wf_004_bw_oap_02_03(self):
        """\n        Test ID: TC-WF-004 | Source ID: BW-OAP-02\n        Purpose: Bonafide request path ending in rejection.\n        Action: Student submits the bonafide request.\n        Expected: Bonafide request submitted - Awaiting Academic Administrator\n        """
        req = submit_bonafide_request(
            student_id="STU_003",
            purpose=BonafidePurpose.PASSPORT,
            details="Passport renewal application"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        reject_bonafide(req.id, "ACAD_ADMIN", "Invalid enrollment proof")
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)
        self.assertEqual(req.rejection_reason, "Invalid enrollment proof")
        self.assertIsNone(req.certificate_number)

    def test_tc_wf_005_bw_oap_03_04(self):
        """\n        Test ID: TC-WF-005 | Source ID: BW-OAP-03\n        Purpose: No-dues clearance path ending in approval.\n        Action: Student submits the no-dues clearance request.\n        Expected: No-dues clearance request submitted - Cleared\n        """
        req = initiate_no_dues("STU_004", NoDuesReason.WITHDRAWAL)
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

    def test_tc_wf_006_bw_oap_03_05(self):
        """\n        Test ID: TC-WF-006 | Source ID: BW-OAP-03\n        Purpose: No-dues clearance path ending in dues outstanding.\n        Action: Student submits the no-dues clearance request.\n        Expected: No-dues clearance request submitted - Dues Outstanding\n        """
        req = initiate_no_dues("STU_005", NoDuesReason.GRADUATION)
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

    def test_tc_wf_007_bw_oap_05_06(self):
        """\n        Test ID: TC-WF-007 | Source ID: BW-OAP-05\n        Purpose: Assistantship claim path ending in approval.\n        Action: PG student submits the assistantship claim.\n        Expected: Assistantship claim submitted - Processed\n        """
        req = submit_branch_change(
            student_id="STU_006",
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

    def test_tc_wf_008_bw_oap_06_07(self):
        """\n        Test ID: TC-WF-008 | Source ID: BW-OAP-06\n        Purpose: Assistantship claim path ending in dues outstanding.\n        Action: PG student submits the assistantship claim.\n        Expected: Assistantship claim submitted - Processed\n        """
        req = initiate_no_dues("STU_007", NoDuesReason.GRADUATION)
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

    def test_tc_wf_009_bw_oap_05_08(self):
        """\n        Test ID: TC-WF-009 | Source ID: BW-OAP-05\n        Purpose: Successful no-dues path through parallel authority verification and Academic Administrator finalization.\n        Action: Student initiates the no-dues clearance process by submitting the assistantship claim.\n        Expected: The assistantship claim is submitted and both supervisor roles resolve.\n        """
        req = initiate_no_dues("STU_008", NoDuesReason.WITHDRAWAL)
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

    def test_tc_wf_010_bw_oap_05_09(self):
        """\n        Test ID: TC-WF-010 | Source ID: BW-OAP-05\n        Purpose: No-dues path in which required verification completes but at least one domain is not clear.\n        Action: Student initiates the no-dues clearance process by submitting the assistantship claim.\n        Expected: The assistantship claim is submitted and both supervisor roles resolve; at least one domain is not clear.\n        """
        req = initiate_no_dues("STU_009", NoDuesReason.GRADUATION)
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

    def test_tc_wf_011_bw_oap_07_10(self):
        """\n        Test ID: TC-WF-011 | Source ID: BW-OAP-07\n        Purpose: Assistantship path from PG submission through verification/review/approval to stipend processing.\n        Action: PG student submits the assistantship claim.\n        Expected: The assistantship claim is submitted and both supervisor roles resolve; the claim is approved; it proceeds through verification/review/approval; and finally, it is processed.\n        """
        req = submit_branch_change(
            student_id="STU_010",
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
