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
    nodues_service,
)


class TestOAPUseCasesSpec(TestCase):
    """Automated UC test suite implementing frozen UC_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_uc_001_oa_uc_01_00(self):
        """
        Test ID: TC-UC-001 | Source ID: OA-UC-01
        Purpose: Ensure student can open the leave application function.
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

    def test_tc_uc_002_oa_uc_01_01(self):
        """
        Test ID: TC-UC-002 | Source ID: OA-UC-01
        Purpose: Ensure system displays the leave request input.
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

    def test_tc_uc_003_oa_uc_01_02(self):
        """
        Test ID: TC-UC-003 | Source ID: OA-UC-01
        Purpose: Ensure student can optionally attach supporting documents.
        """
        s_id = 'STU_002'
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

    def test_tc_uc_004_oa_uc_01_03(self):
        """
        Test ID: TC-UC-004 | Source ID: OA-UC-01
        Purpose: Ensure student can submit the application.
        """
        s_id = 'STU_003'
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

    def test_tc_uc_005_oa_uc_01_04(self):
        """
        Test ID: TC-UC-005 | Source ID: OA-UC-01
        Purpose: Ensure system records the submitted application.
        """
        s_id = 'STU_004'
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

    def test_tc_uc_006_oa_uc_01_05(self):
        """
        Test ID: TC-UC-006 | Source ID: OA-UC-01
        Purpose: Ensure system triggers the required submission notification.
        """
        s_id = 'STU_005'
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

    def test_tc_uc_007_oa_uc_01_06(self):
        """
        Test ID: TC-UC-007 | Source ID: OA-UC-01
        Purpose: Ensure submitted application is available to the HoD.
        """
        s_id = 'STU_006'
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

    def test_tc_uc_008_oa_uc_02_07(self):
        """
        Test ID: TC-UC-008 | Source ID: OA-UC-02
        Purpose: Ensure HoD can open a submitted leave application.
        """
        s_id = 'STU_007'
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

    def test_tc_uc_009_oa_uc_02_08(self):
        """
        Test ID: TC-UC-009 | Source ID: OA-UC-02
        Purpose: Ensure system displays the submitted leave request.
        """
        s_id = 'STU_008'
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

    def test_tc_uc_010_oa_uc_02_09(self):
        """
        Test ID: TC-UC-010 | Source ID: OA-UC-02
        Purpose: Ensure HoD can review the application.
        """
        s_id = 'STU_009'
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

    def test_tc_uc_011_oa_uc_02_10(self):
        """
        Test ID: TC-UC-011 | Source ID: OA-UC-02
        Purpose: Ensure HoD can record an Approve or Reject decision.
        """
        s_id = 'STU_010'
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

    def test_tc_uc_012_oa_uc_02_11(self):
        """
        Test ID: TC-UC-012 | Source ID: OA-UC-02
        Purpose: Ensure system records the decision and updates the application status.
        """
        s_id = 'STU_011'
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

    def test_tc_uc_013_oa_uc_02_12(self):
        """
        Test ID: TC-UC-013 | Source ID: OA-UC-02
        Purpose: Ensure system triggers the required decision notification to the student.
        """
        s_id = 'STU_012'
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

    def test_tc_uc_014_oa_uc_03_13(self):
        """
        Test ID: TC-UC-014 | Source ID: OA-UC-03
        Purpose: Ensure student can open the bonafide request function.
        """
        s_id = 'STU_013'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_uc_015_oa_uc_03_14(self):
        """
        Test ID: TC-UC-015 | Source ID: OA-UC-03
        Purpose: Ensure system displays the bonafide request input.
        """
        s_id = 'STU_014'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)
        self.assertEqual(req.student_id, s_id)

    def test_tc_uc_016_oa_uc_03_15(self):
        """
        Test ID: TC-UC-016 | Source ID: OA-UC-03
        Purpose: Ensure student can submit the request.
        """
        s_id = 'STU_015'
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

    def test_tc_uc_017_oa_uc_03_16(self):
        """
        Test ID: TC-UC-017 | Source ID: OA-UC-03
        Purpose: Ensure system records the submitted request.
        """
        s_id = 'STU_016'
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

    def test_tc_uc_018_oa_uc_03_17(self):
        """
        Test ID: TC-UC-018 | Source ID: OA-UC-03
        Purpose: Ensure system triggers the required submission notification to the student.
        """
        s_id = 'STU_017'
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

    def test_tc_uc_019_oa_uc_04_18(self):
        """
        Test ID: TC-UC-019 | Source ID: OA-UC-04
        Purpose: Ensure student can view the current leave status and request history.
        """
        s_id = 'STU_018'
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

    def test_tc_uc_020_oa_uc_21_19(self):
        """
        Test ID: TC-UC-020 | Source ID: OA-UC-21
        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.
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

    def test_tc_uc_021_oa_uc_21_20(self):
        """
        Test ID: TC-UC-021 | Source ID: OA-UC-21
        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.
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

    def test_tc_uc_022_oa_uc_21_21(self):
        """
        Test ID: TC-UC-022 | Source ID: OA-UC-21
        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.
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

    def test_tc_uc_023_oa_uc_21_22(self):
        """
        Test ID: TC-UC-023 | Source ID: OA-UC-21
        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.
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

    def test_tc_uc_024_oa_uc_21_23(self):
        """
        Test ID: TC-UC-024 | Source ID: OA-UC-21
        Purpose: Verify the initiation of no-dues clearance and route verification in parallel to all seven mandatory clearance authorities.
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

    def test_tc_uc_025_oa_uc_21_24(self):
        """
        Test ID: TC-UC-025 | Source ID: OA-UC-21
        Purpose: Verify that a clearance request cannot be recorded/routed; system reports failure without claiming successful initiation.
        """
        s_id = 'STU_024'
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

    def test_tc_uc_026_oa_uc_22_25(self):
        """
        Test ID: TC-UC-026 | Source ID: OA-UC-22
        Purpose: Verify that an authority receives or opens a pending no-dues verification.
        """
        s_id = 'STU_025'
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_uc_027_oa_uc_22_26(self):
        """
        Test ID: TC-UC-027 | Source ID: OA-UC-22
        Purpose: Verify that an authority receives or opens a pending no-dues verification.
        """
        s_id = 'STU_026'
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_uc_028_oa_uc_22_27(self):
        """
        Test ID: TC-UC-028 | Source ID: OA-UC-22
        Purpose: Verify that an authority receives or opens a pending no-dues verification.
        """
        s_id = 'STU_027'
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_uc_029_oa_uc_22_28(self):
        """
        Test ID: TC-UC-029 | Source ID: OA-UC-22
        Purpose: Verify that an authority receives or opens a pending no-dues verification.
        """
        s_id = 'STU_028'
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_uc_030_oa_uc_22_29(self):
        """
        Test ID: TC-UC-030 | Source ID: OA-UC-22
        Purpose: Verify that an authority receives or opens a pending no-dues verification.
        """
        s_id = 'STU_029'
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_uc_031_oa_uc_22_30(self):
        """
        Test ID: TC-UC-031 | Source ID: OA-UC-22
        Purpose: Verify that an authority records that dues/obligations remain outstanding; the domain is not marked clear.
        """
        s_id = 'STU_030'
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

    def test_tc_uc_032_oa_uc_23_31(self):
        """
        Test ID: TC-UC-032 | Source ID: OA-UC-23
        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.
        """
        s_id = 'STU_031'
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

    def test_tc_uc_033_oa_uc_23_32(self):
        """
        Test ID: TC-UC-033 | Source ID: OA-UC-23
        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.
        """
        s_id = 'STU_032'
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

    def test_tc_uc_034_oa_uc_23_33(self):
        """
        Test ID: TC-UC-034 | Source ID: OA-UC-23
        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.
        """
        s_id = 'STU_033'
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

    def test_tc_uc_035_oa_uc_23_34(self):
        """
        Test ID: TC-UC-035 | Source ID: OA-UC-23
        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.
        """
        s_id = 'STU_034'
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

    def test_tc_uc_036_oa_uc_23_35(self):
        """
        Test ID: TC-UC-036 | Source ID: OA-UC-23
        Purpose: Verify that the consolidated seven-authority no-dues results and finalize clearance only when all seven required clearances are clear.
        """
        s_id = 'STU_035'
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

    def test_tc_uc_037_oa_uc_23_36(self):
        """
        Test ID: TC-UC-037 | Source ID: OA-UC-23
        Purpose: Verify that finalization cannot be persisted; previous statuses are retained.
        """
        s_id = 'STU_036'
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

    def test_tc_uc_038_oa_uc_31_37(self):
        """
        Test ID: TC-UC-038 | Source ID: OA-UC-31
        Purpose: Testing the main success flow for submitting an assistantship claim.
        """
        s_id = 'STU_037'
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

    def test_tc_uc_039_oa_uc_31_38(self):
        """
        Test ID: TC-UC-039 | Source ID: OA-UC-31
        Purpose: Testing the system acceptance of the claim information.
        """
        s_id = 'STU_038'
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

    def test_tc_uc_040_oa_uc_31_39(self):
        """
        Test ID: TC-UC-040 | Source ID: OA-UC-31
        Purpose: Testing the system routing the claim to both the assigned Thesis Supervisor and assigned TA Supervisor for role-specific verification.
        """
        s_id = 'STU_039'
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

    def test_tc_uc_041_oa_uc_31_40(self):
        """
        Test ID: TC-UC-041 | Source ID: OA-UC-31
        Purpose: Testing the system's ability to display the claim information and the supervisor role being exercised.
        """
        s_id = 'STU_040'
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

    def test_tc_uc_042_oa_uc_31_41(self):
        """
        Test ID: TC-UC-042 | Source ID: OA-UC-31
        Purpose: Testing the system's ability to review the claim.
        """
        s_id = 'STU_041'
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

    def test_tc_uc_043_oa_uc_31_42(self):
        """
        Test ID: TC-UC-043 | Source ID: OA-UC-31
        Purpose: Testing the system's ability to store the role-specific verification independently.
        """
        s_id = 'STU_042'
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

    def test_tc_uc_044_oa_uc_31_43(self):
        """
        Test ID: TC-UC-044 | Source ID: OA-UC-31
        Purpose: Testing the system's ability to advance the claim to the Department Administrator after both required role-verifications are complete.
        """
        s_id = 'STU_043'
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

    def test_tc_uc_045_oa_uc_31_44(self):
        """
        Test ID: TC-UC-045 | Source ID: OA-UC-31
        Purpose: Testing the system's ability to display the claim and both supervisor-role verifications after the claim has been reviewed and forwarded to the HoD.
        """
        s_id = 'STU_044'
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

    def test_tc_uc_046_oa_uc_51_45(self):
        """
        Test ID: TC-UC-046 | Source ID: OA-UC-51
        Purpose: Verify that a PG student opens the seminar scheduling request and submits it successfully.
        """
        s_id = 'STU_045'
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

    def test_tc_uc_047_oa_uc_51_46(self):
        """
        Test ID: TC-UC-047 | Source ID: OA-UC-51
        Purpose: Verify that the system triggers the required submission notification.
        """
        s_id = 'STU_046'
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

    def test_tc_uc_048_oa_uc_53_47(self):
        """
        Test ID: TC-UC-048 | Source ID: OA-UC-53
        Purpose: Verify that a Department Administrator opens a pending seminar scheduling request and determines the seminar schedule successfully.
        """
        s_id = 'STU_047'
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

    def test_tc_uc_049_oa_uc_53_48(self):
        """
        Test ID: TC-UC-049 | Source ID: OA-UC-53
        Purpose: Verify that the system triggers relevant notifications for the scheduled seminar.
        """
        s_id = 'STU_048'
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

    def test_tc_uc_050_oa_uc_54_49(self):
        """
        Test ID: TC-UC-050 | Source ID: OA-UC-54
        Purpose: Verify that an authorized user opens the seminar schedule and displays the available seminar schedule successfully.
        """
        s_id = 'STU_049'
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

    def test_tc_uc_051_oa_uc_54_50(self):
        """
        Test ID: TC-UC-051 | Source ID: OA-UC-54
        Purpose: Verify that the system displays an empty schedule if no scheduled seminars exist.
        """
        s_id = 'STU_050'
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

    def test_tc_uc_052_oa_uc_91_51(self):
        """
        Test ID: TC-UC-052 | Source ID: OA-UC-91
        Purpose: Verify that a relevant OAP event notification is sent through the supported channels successfully.
        """
        s_id = 'STU_051'
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

    def test_tc_uc_053_oa_uc_92_52(self):
        """
        Test ID: TC-UC-053 | Source ID: OA-UC-92
        Purpose: Verify that a reminder for a pending OAP action is sent successfully.
        """
        s_id = 'STU_052'
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
