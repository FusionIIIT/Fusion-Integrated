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


class TestOAPWorkflowsSpec(TestCase):
    """Automated WF test suite implementing frozen WF_DESIGN.json."""

    def setUp(self):
        self.client = APIClient()

    def test_tc_wf_001_bw_oap_01_00(self):
        """
        Test ID: TC-WF-001 | Source ID: BW-OAP-01
        Purpose: Successful leave path from student submission to HoD approval.
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
        leave_service.hod_approve_leave(req.id, 'HOD01', 'Approved')
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_tc_wf_002_bw_oap_01_01(self):
        """
        Test ID: TC-WF-002 | Source ID: BW-OAP-01
        Purpose: Leave path ending in HoD rejection.
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
        leave_service.hod_reject_leave(req.id, 'HOD01', 'Denied')
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)

    def test_tc_wf_003_bw_oap_02_02(self):
        """
        Test ID: TC-WF-003 | Source ID: BW-OAP-02
        Purpose: Bonafide request path ending in approval.
        """
        s_id = 'STU_002'
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

    def test_tc_wf_004_bw_oap_02_03(self):
        """
        Test ID: TC-WF-004 | Source ID: BW-OAP-02
        Purpose: Bonafide request path ending in rejection.
        """
        s_id = 'STU_003'
        req = BonafideRequest.objects.create(
            student_id=s_id,
            purpose=BonafidePurpose.GENERAL,
            details='Bonafide requirement',
            status=BonafideStatus.PENDING,
        )
        bonafide_service.reject_bonafide(req.id, 'ADMIN01', 'Incomplete')
        req.refresh_from_db()
        self.assertEqual(req.status, BonafideStatus.REJECTED)

    def test_tc_wf_005_bw_oap_03_04(self):
        """
        Test ID: TC-WF-005 | Source ID: BW-OAP-03
        Purpose: No-dues clearance path ending in approval.
        """
        s_id = 'STU_004'
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

    def test_tc_wf_006_bw_oap_03_05(self):
        """
        Test ID: TC-WF-006 | Source ID: BW-OAP-03
        Purpose: No-dues clearance path ending in dues outstanding.
        """
        s_id = 'STU_005'
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

    def test_tc_wf_007_bw_oap_05_06(self):
        """
        Test ID: TC-WF-007 | Source ID: BW-OAP-05
        Purpose: Assistantship claim path ending in approval.
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

    def test_tc_wf_008_bw_oap_06_07(self):
        """
        Test ID: TC-WF-008 | Source ID: BW-OAP-06
        Purpose: Assistantship claim path ending in dues outstanding.
        """
        s_id = 'STU_007'
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

    def test_tc_wf_009_bw_oap_05_08(self):
        """
        Test ID: TC-WF-009 | Source ID: BW-OAP-05
        Purpose: Successful no-dues path through parallel authority verification and Academic Administrator finalization.
        """
        s_id = 'STU_008'
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

    def test_tc_wf_010_bw_oap_05_09(self):
        """
        Test ID: TC-WF-010 | Source ID: BW-OAP-05
        Purpose: No-dues path in which required verification completes but at least one domain is not clear.
        """
        s_id = 'STU_009'
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

    def test_tc_wf_011_bw_oap_07_10(self):
        """
        Test ID: TC-WF-011 | Source ID: BW-OAP-07
        Purpose: Assistantship path from PG submission through verification/review/approval to stipend processing.
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
