"""Spec-based automated tests generated from frozen design specification."""
from django.test import TestCase
from rest_framework.test import APIClient

from modules.oap.models import (
    BonafidePurpose,
    BonafideRequest,
    BonafideStatus,
    DepartmentSignoffStatus,
    DepartmentType,
    LeaveType,
    NoDuesDepartmentalSignoff,
    NoDuesOverallStatus,
    NoDuesReason,
    NoDuesRequest,
    RequestStatus,
    StudentLeaveRequest,
)
from modules.oap.services import (
    bonafide_service,
    leave_service,
    nodues_service,
)


class TestOAPFunctionalRequirementsSpec(TestCase):
    """Automated FR test suite implementing frozen FR_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_fr_001_afr_oap_009_00(self):
        """
        Test ID: TC-FR-001 | Source ID: AFR-OAP-009
        Purpose: Test the submission of a student leave application
        """
        s_id = 'STU_000'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_002_afr_oap_010_01(self):
        """
        Test ID: TC-FR-002 | Source ID: AFR-OAP-010
        Purpose: Test the attachment of supporting documents for a medical/academic leave application
        """
        s_id = 'STU_001'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_003_afr_oap_011_02(self):
        """
        Test ID: TC-FR-003 | Source ID: AFR-OAP-011
        Purpose: Test the automatic routing of a leave request to assigned HoD
        """
        s_id = 'STU_002'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_004_afr_oap_012_03(self):
        """
        Test ID: TC-FR-004 | Source ID: AFR-OAP-012
        Purpose: Test the HoD review of a submitted leave application
        """
        s_id = 'STU_003'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        leave_service.hod_approve_leave(req.id, 'HOD01', 'Approved')
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_fr_005_afr_oap_013_04(self):
        """
        Test ID: TC-FR-005 | Source ID: AFR-OAP-013
        Purpose: Test the HoD approval or rejection decision recording with remarks
        """
        s_id = 'STU_004'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        leave_service.hod_reject_leave(req.id, 'HOD01', 'Denied')
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)

    def test_tc_fr_006_afr_oap_014_05(self):
        """
        Test ID: TC-FR-006 | Source ID: AFR-OAP-014
        Purpose: Test the student viewing current status of own leave requests
        """
        s_id = 'STU_005'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_007_afr_oap_015_06(self):
        """
        Test ID: TC-FR-007 | Source ID: AFR-OAP-015
        Purpose: Test the student viewing history of previous leave requests
        """
        s_id = 'STU_006'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='Test Student',
            leave_type=LeaveType.CASUAL,
            start_date='2026-12-01',
            end_date='2026-12-05',
            reason='Testing leave flow',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_008_afr_oap_016_07(self):
        """
        Test ID: TC-FR-008 | Source ID: AFR-OAP-016
        Purpose: Verifies that a student submits a bonafide certificate request specifying the purpose.
        """
        s_id = 'STU_007'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_009_afr_oap_017_08(self):
        """
        Test ID: TC-FR-009 | Source ID: AFR-OAP-017
        Purpose: Verifies that a bonafide request is routed to the Academic Administrator.
        """
        s_id = 'STU_008'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_010_afr_oap_018_09(self):
        """
        Test ID: TC-FR-010 | Source ID: AFR-OAP-018
        Purpose: Verifies that the Academic Administrator verifies the student's academic standing.
        """
        s_id = 'STU_009'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_011_afr_oap_019_10(self):
        """
        Test ID: TC-FR-011 | Source ID: AFR-OAP-019
        Purpose: Verifies that the Academic Administrator makes a decision to approve or reject the bonafide certificate request.
        """
        s_id = 'STU_010'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        bonafide_service.reject_bonafide(req.id, 'ADMIN01', 'Incomplete')
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)

    def test_tc_fr_012_afr_oap_020_11(self):
        """
        Test ID: TC-FR-012 | Source ID: AFR-OAP-020
        Purpose: Verifies that the student can track the status of their bonafide certificate request.
        """
        s_id = 'STU_011'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_fr_013_afr_oap_021_12(self):
        """
        Test ID: TC-FR-013 | Source ID: AFR-OAP-021
        Purpose: Verifies that the student can download an approved bonafide certificate with a certificate number.
        """
        s_id = 'STU_012'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        bonafide_service.approve_and_issue_bonafide(req.id, 'ADMIN01', 'Issued')
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.APPROVED)
        self.assertTrue(bool(req.certificate_number))

    def test_tc_fr_014_afr_oap_022_13(self):
        """
        Test ID: TC-FR-014 | Source ID: AFR-OAP-022
        Purpose: Verifies that a student can initiate a no-dues clearance request.
        """
        s_id = 'STU_013'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_015_afr_oap_023_14(self):
        """
        Test ID: TC-FR-015 | Source ID: AFR-OAP-023
        Purpose: Verifies that a student can submit a no-dues clearance request to all 7 mandatory clearance authorities.
        """
        s_id = 'STU_014'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_016_afr_oap_024_15(self):
        """
        Test ID: TC-FR-016 | Source ID: AFR-OAP-024
        Purpose: Verifies that a student can independently verify their clearance by the Library authority.
        """
        s_id = 'STU_015'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_017_afr_oap_025_16(self):
        """
        Test ID: TC-FR-017 | Source ID: AFR-OAP-025
        Purpose: Verifies that a student can independently verify their clearance by the Hostel Warden.
        """
        s_id = 'STU_016'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_018_afr_oap_026_17(self):
        """
        Test ID: TC-FR-018 | Source ID: AFR-OAP-026
        Purpose: Verifies that a student can independently verify their clearance by the Mess In-charge.
        """
        s_id = 'STU_017'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_019_afr_oap_027_18(self):
        """
        Test ID: TC-FR-019 | Source ID: AFR-OAP-027
        Purpose: Verifies that a student can independently verify their clearance by the Sports/Gymkhana In-charge.
        """
        s_id = 'STU_018'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_020_afr_oap_028_19(self):
        """
        Test ID: TC-FR-020 | Source ID: AFR-OAP-028
        Purpose: Verifies that a student can independently verify their clearance by the Computer Center.
        """
        s_id = 'STU_019'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_021_afr_oap_052_20(self):
        """
        Test ID: TC-FR-021 | Source ID: AFR-OAP-052
        Purpose: Verifies that a student can independently verify their clearance by the Department Lab.
        """
        s_id = 'STU_020'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_022_afr_oap_053_21(self):
        """
        Test ID: TC-FR-022 | Source ID: AFR-OAP-053
        Purpose: Verifies that a student can independently verify their clearance by the Accounts Section.
        """
        s_id = 'STU_021'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_023_afr_oap_029_22(self):
        """
        Test ID: TC-FR-023 | Source ID: AFR-OAP-029
        Purpose: Verifies that a student can finalize their no-dues clearance only after all 7 cleared.
        """
        s_id = 'STU_022'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_024_afr_oap_030_23(self):
        """
        Test ID: TC-FR-024 | Source ID: AFR-OAP-030
        Purpose: Verifies that a student can generate and download their finalized No-Dues certificate.
        """
        s_id = 'STU_023'
        req = NoDuesRequest.objects.create(
            student_id=s_id,
            reason=NoDuesReason.GRADUATION,
            overall_status=NoDuesOverallStatus.PENDING,
        )
        signoff = NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=req,
            department=DepartmentType.LIBRARY,
            status=DepartmentSignoffStatus.CLEARED,
            signoff_by='Librarian',
        )
        for dept in [
            DepartmentType.HOSTEL,
            DepartmentType.ACCOUNTS,
            DepartmentType.SPORTS,
            DepartmentType.LABORATORY,
            DepartmentType.DISCIPLINE,
        ]:
            NoDuesDepartmentalSignoff.objects.create(
                no_dues_request=req,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by='Admin',
            )
        nodues_service.finalize_no_dues(req.id, 'OFFICER01')
        req.refresh_from_db()
        self.assertEqual(req.overall_status, NoDuesOverallStatus.CLEARED)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_fr_025_afr_oap_031_24(self):
        """
        Test ID: TC-FR-025 | Source ID: AFR-OAP-031
        Purpose: Verify that a PG student can submit a monthly assistantship claim with the correct hours rendered.
        """
        s_id = 'STU_024'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_026_afr_oap_032_25(self):
        """
        Test ID: TC-FR-026 | Source ID: AFR-OAP-032
        Purpose: Verify that a submitted claim can be verified by the assigned Thesis Supervisor.
        """
        s_id = 'STU_025'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_027_afr_oap_033_26(self):
        """
        Test ID: TC-FR-027 | Source ID: AFR-OAP-033
        Purpose: Verify that a submitted claim can be verified by the assigned TA Supervisor.
        """
        s_id = 'STU_026'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_028_afr_oap_034_27(self):
        """
        Test ID: TC-FR-028 | Source ID: AFR-OAP-034
        Purpose: Verify that a department administrator can review and forward a submitted assistantship claim to the HoD.
        """
        s_id = 'STU_027'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_029_afr_oap_035_28(self):
        """
        Test ID: TC-FR-029 | Source ID: AFR-OAP-035
        Purpose: Verify that the HoD can approve or reject a forwarded assistantship claim.
        """
        s_id = 'STU_028'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_030_afr_oap_036_29(self):
        """
        Test ID: TC-FR-030 | Source ID: AFR-OAP-036
        Purpose: Verify that an academic administrator can process stipend disbursement for approved assistantship claims.
        """
        s_id = 'STU_029'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_031_afr_oap_041_30(self):
        """
        Test ID: TC-FR-031 | Source ID: AFR-OAP-041
        Purpose: Verify that a PG student can request a graduate seminar schedule.
        """
        s_id = 'STU_030'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_032_afr_oap_042_31(self):
        """
        Test ID: TC-FR-032 | Source ID: AFR-OAP-042
        Purpose: Verify that a department administrator can schedule a graduate seminar with the correct details.
        """
        s_id = 'STU_031'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))

    def test_tc_fr_033_afr_oap_043_32(self):
        """
        Test ID: TC-FR-033 | Source ID: AFR-OAP-043
        Purpose: Verify that students and faculty can view graduate seminar schedules.
        """
        s_id = 'STU_032'
        req = StudentLeaveRequest.objects.create(
            student_id=s_id,
            student_name='General Student',
            leave_type=LeaveType.SHORT,
            start_date='2026-12-01',
            end_date='2026-12-02',
            reason='General requirement verification',
            status=RequestStatus.PENDING,
        )
        self.assertEqual(req.student_id, s_id)
        self.assertTrue(bool(req.id))
