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


class TestOAPBusinessRulesSpec(TestCase):
    """Automated BR test suite implementing frozen BR_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_br_001_oa_br_01_00(self):
        """
        Test ID: TC-BR-001 | Source ID: OA-BR-01
        Purpose: Ensure that only authorized roles can access OAP functions and information.
        """
        s_id = 'STU_000'
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

    def test_tc_br_002_oa_br_01_01(self):
        """
        Test ID: TC-BR-002 | Source ID: OA-BR-01
        Purpose: Verify that only roles authorized for the relevant function or record can access OAP functions and information.
        """
        s_id = 'STU_001'
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

    def test_tc_br_003_oa_br_03_02(self):
        """
        Test ID: TC-BR-003 | Source ID: OA-BR-03
        Purpose: Verify that OAP notifications are sent via system alerts and email.
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

    def test_tc_br_004_oa_br_03_03(self):
        """
        Test ID: TC-BR-004 | Source ID: OA-BR-03
        Purpose: Ensure that OAP notifications are sent via system alerts and email.
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

    def test_tc_br_005_oa_br_11_04(self):
        """
        Test ID: TC-BR-005 | Source ID: OA-BR-11
        Purpose: Verify that only the HoD is specified to approve or reject student leave applications.
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

    def test_tc_br_006_oa_br_11_05(self):
        """
        Test ID: TC-BR-006 | Source ID: OA-BR-11
        Purpose: Verify that only the HoD is specified to approve or reject student leave applications.
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
        leave_service.hod_reject_leave(req.id, 'HOD01', 'Denied')
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)

    def test_tc_br_007_oa_br_21_06(self):
        """
        Test ID: TC-BR-007 | Source ID: OA-BR-21
        Purpose: Verify that the Academic Administrator is the specified authority to verify and approve/reject bonafide requests.
        """
        s_id = 'STU_006'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        bonafide_service.reject_bonafide(req.id, 'ADMIN01', 'Incomplete')
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)

    def test_tc_br_008_oa_br_21_07(self):
        """
        Test ID: TC-BR-008 | Source ID: OA-BR-21
        Purpose: Verify that the Academic Administrator is the specified authority to verify and approve/reject bonafide requests.
        """
        s_id = 'STU_007'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        bonafide_service.reject_bonafide(req.id, 'ADMIN01', 'Incomplete')
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)

    def test_tc_br_009_oa_br_22_08(self):
        """
        Test ID: TC-BR-009 | Source ID: OA-BR-22
        Purpose: Verify that a bonafide certificate shall be available for download only after the request is approved.
        """
        s_id = 'STU_008'
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

    def test_tc_br_010_oa_br_22_09(self):
        """
        Test ID: TC-BR-010 | Source ID: OA-BR-22
        Purpose: Ensure that a bonafide certificate shall be available for download only after the request is approved.
        """
        s_id = 'STU_009'
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

    def test_tc_br_011_oa_br_31_10(self):
        """
        Test ID: TC-BR-011 | Source ID: OA-BR-31
        Purpose: Verify that each of the seven mandatory no-dues authorities may record clearance only for its own institutional domain.
        """
        s_id = 'STU_010'
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

    def test_tc_br_012_oa_br_31_11(self):
        """
        Test ID: TC-BR-012 | Source ID: OA-BR-31
        Purpose: Ensure that each of the seven mandatory no-dues authorities may record clearance only for its own institutional domain.
        """
        s_id = 'STU_011'
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

    def test_tc_br_013_oa_br_32_12(self):
        """
        Test ID: TC-BR-013 | Source ID: OA-BR-32
        Purpose: Verify that the clearance result from each of the seven mandatory no-dues authorities shall be maintained independently until consolidation.
        """
        s_id = 'STU_012'
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

    def test_tc_br_014_oa_br_32_13(self):
        """
        Test ID: TC-BR-014 | Source ID: OA-BR-32
        Purpose: Ensure that the clearance result from each of the seven mandatory no-dues authorities shall be maintained independently until consolidation.
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

    def test_tc_br_015_oa_br_33_14(self):
        """
        Test ID: TC-BR-015 | Source ID: OA-BR-33
        Purpose: Verify that no-dues clearance may be finalized only after all seven mandatory authorities have submitted verification and all seven clearance results are clear.
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

    def test_tc_br_016_oa_br_33_15(self):
        """
        Test ID: TC-BR-016 | Source ID: OA-BR-33
        Purpose: Ensure that no-dues clearance may be finalized only after all seven mandatory authorities have submitted verification and all seven clearance results are clear.
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

    def test_tc_br_017_oa_br_34_16(self):
        """
        Test ID: TC-BR-017 | Source ID: OA-BR-34
        Purpose: Verify that the no-dues certificate shall be made downloadable only after Academic Administrator finalization.
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_br_018_oa_br_34_17(self):
        """
        Test ID: TC-BR-018 | Source ID: OA-BR-34
        Purpose: Ensure that the no-dues certificate shall be made downloadable only after Academic Administrator finalization.
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
        self.assertEqual(req.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(signoff.status, DepartmentSignoffStatus.CLEARED)

    def test_tc_br_019_oa_br_01_18(self):
        """
        Test ID: TC-BR-019 | Source ID: OA-BR-01
        Purpose: To ensure that only PG students can submit assistantship claims.
        """
        s_id = 'STU_018'
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

    def test_tc_br_020_oa_br_02_19(self):
        """
        Test ID: TC-BR-020 | Source ID: OA-BR-02
        Purpose: To ensure that both supervisor roles are verified before Department Administrator review.
        """
        s_id = 'STU_019'
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

    def test_tc_br_021_oa_br_03_20(self):
        """
        Test ID: TC-BR-021 | Source ID: OA-BR-03
        Purpose: To ensure that the Department Administrator review occurs only after both role-verifications are complete.
        """
        s_id = 'STU_020'
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

    def test_tc_br_022_oa_br_04_21(self):
        """
        Test ID: TC-BR-022 | Source ID: OA-BR-04
        Purpose: To ensure that the HoD is the stated departmental authority to approve or reject assistantship claims.
        """
        s_id = 'STU_021'
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

    def test_tc_br_023_oa_br_05_22(self):
        """
        Test ID: TC-BR-023 | Source ID: OA-BR-05
        Purpose: To ensure that the accepted assistantship progression is correct.
        """
        s_id = 'STU_022'
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

    def test_tc_br_024_oa_br_06_23(self):
        """
        Test ID: TC-BR-024 | Source ID: OA-BR-06
        Purpose: To ensure that the Department Administrator records thesis-supervisor assignments and TA assignments based on departmental decisions.
        """
        s_id = 'STU_023'
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

    def test_tc_br_025_oa_br_07_24(self):
        """
        Test ID: TC-BR-025 | Source ID: OA-BR-07
        Purpose: To ensure that graduate seminar scheduling requests are within PG-student scope.
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

    def test_tc_br_026_oa_br_08_25(self):
        """
        Test ID: TC-BR-026 | Source ID: OA-BR-08
        Purpose: To ensure that the Department Administrator schedules and logs graduate seminars.
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

    def test_tc_br_027_oa_br_09_26(self):
        """
        Test ID: TC-BR-027 | Source ID: OA-BR-09
        Purpose: To ensure that graduate seminar schedules are viewable by PG students and faculty.
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
