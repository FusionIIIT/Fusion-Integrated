"""Unit tests for OAP application services and state workflows."""
from __future__ import annotations

import datetime
from decimal import Decimal

from django.test import TestCase

from modules.oap.domain.exceptions import IneligibleRequestError, OAPDomainError
from modules.oap.models.bonafide import BonafideStatus
from modules.oap.models.branch_change import BranchChangeStatus
from modules.oap.models.leave import LeaveType, RequestStatus
from modules.oap.models.nodues import (
    DepartmentSignoffStatus,
    DepartmentType,
    NoDuesOverallStatus,
    NoDuesRequest,
)
from modules.oap.services.bonafide_service import (
    approve_and_issue_bonafide,
    reject_bonafide,
    submit_bonafide_request,
)
from modules.oap.services.branch_change_service import (
    allocate_and_sanction,
    submit_branch_change,
    verify_branch_change,
)
from modules.oap.services.leave_service import (
    cancel_leave,
    hod_approve_leave,
    hod_reject_leave,
    recommend_leave,
    submit_leave_application,
)
from modules.oap.services.nodues_service import (
    finalize_no_dues,
    initiate_no_dues,
    record_department_signoff,
)


class TestOAPServices(TestCase):
    def test_submit_leave_validation(self):
        # Invalid date range
        with self.assertRaises(OAPDomainError):
            submit_leave_application(
                student_id="24BCS205",
                student_name="Rahul Kumar",
                leave_type=LeaveType.CASUAL,
                start_date=datetime.date(2026, 11, 28),
                end_date=datetime.date(2026, 11, 26),
                reason="Invalid dates",
            )

        # Medical leave > 3 days without document
        with self.assertRaises(OAPDomainError):
            submit_leave_application(
                student_id="24BCS205",
                student_name="Rahul Kumar",
                leave_type=LeaveType.MEDICAL,
                start_date=datetime.date(2026, 11, 20),
                end_date=datetime.date(2026, 11, 25),
                reason="Flu",
                document_url=None,
            )

        # Valid leave
        leave = submit_leave_application(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL,
            start_date=datetime.date(2026, 11, 20),
            end_date=datetime.date(2026, 11, 22),
            reason="Family event",
        )
        self.assertEqual(leave.status, RequestStatus.PENDING)

        # Overlapping leave refused
        with self.assertRaises(OAPDomainError):
            submit_leave_application(
                student_id="24BCS205",
                student_name="Rahul Kumar",
                leave_type=LeaveType.SHORT,
                start_date=datetime.date(2026, 11, 21),
                end_date=datetime.date(2026, 11, 23),
                reason="Overlap",
            )

    def test_leave_approval_pipeline(self):
        leave = submit_leave_application(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL,
            start_date=datetime.date(2026, 12, 1),
            end_date=datetime.date(2026, 12, 2),
            reason="Conference",
        )
        recommend_leave(leave.pk, supervisor_id="SUP_01", remarks="Approved to attend")
        leave.refresh_from_db()
        self.assertEqual(leave.status, RequestStatus.RECOMMENDED)

        hod_approve_leave(leave.pk, hod_id="HOD_CSE", remarks="Sanctioned")
        leave.refresh_from_db()
        self.assertEqual(leave.status, RequestStatus.APPROVED)

    def test_leave_reject_and_cancel_services(self):
        l1 = submit_leave_application(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL,
            start_date=datetime.date(2026, 12, 10),
            end_date=datetime.date(2026, 12, 11),
            reason="Medical",
        )
        hod_reject_leave(l1.pk, hod_id="HOD_CSE", remarks="Denied")
        l1.refresh_from_db()
        self.assertEqual(l1.status, RequestStatus.REJECTED)

        l2 = submit_leave_application(
            student_id="24BCS205",
            student_name="Rahul Kumar",
            leave_type=LeaveType.CASUAL,
            start_date=datetime.date(2026, 12, 15),
            end_date=datetime.date(2026, 12, 16),
            reason="Personal",
        )
        with self.assertRaises(OAPDomainError):
            cancel_leave(l2.pk, student_id="ANOTHER_STUDENT")
        cancel_leave(l2.pk, student_id="24BCS205")
        l2.refresh_from_db()
        self.assertEqual(l2.status, RequestStatus.CANCELLED)

    def test_bonafide_service(self):
        req = submit_bonafide_request(
            student_id="24BCS205", purpose="VISA", details="German Student Visa"
        )
        self.assertEqual(req.status, BonafideStatus.PENDING)

        # Prevent duplicate pending
        with self.assertRaises(OAPDomainError):
            submit_bonafide_request(student_id="24BCS205", purpose="VISA")

        cert = approve_and_issue_bonafide(req.pk, admin_id="ACAD_OFFICER")
        self.assertTrue(cert.startswith("IIITDMJ/OAP/BONA/"))

        req2 = submit_bonafide_request(
            student_id="24BCS205", purpose="PASSPORT", details="Passport"
        )
        reject_bonafide(req2.pk, admin_id="ACAD_ADMIN", reason="Missing documents")
        req2.refresh_from_db()
        self.assertEqual(req2.status, BonafideStatus.REJECTED)

    def test_no_dues_service(self):
        # Prevent duplicate initiation
        initiate_no_dues(student_id="24BCS205")
        with self.assertRaises(OAPDomainError):
            initiate_no_dues(student_id="24BCS205")

        nd = NoDuesRequest.objects.get(student_id="24BCS205")
        self.assertEqual(nd.overall_status, NoDuesOverallStatus.PENDING)
        self.assertEqual(nd.signoffs.count(), 6)

        # Finalize before all are cleared -> False
        cleared = finalize_no_dues(nd.pk, admin_id="ACAD_ADMIN")
        self.assertFalse(cleared)

        for dept in DepartmentType.values:
            record_department_signoff(
                request_id=nd.pk,
                department=dept,
                status=DepartmentSignoffStatus.CLEARED,
                signoff_by="OFFICER",
            )
        cleared_after = finalize_no_dues(nd.pk, admin_id="ACAD_ADMIN")
        self.assertTrue(cleared_after)
        nd.refresh_from_db()
        self.assertEqual(nd.overall_status, NoDuesOverallStatus.CLEARED)

    def test_branch_change_service(self):
        # Ineligible due to backlogs
        with self.assertRaises(IneligibleRequestError):
            submit_branch_change(
                student_id="24BCS099",
                current_branch="ME",
                preferred_branch_1="CSE",
                preferred_branch_2=None,
                current_cpi=Decimal("8.50"),
                credits_completed=40,
                has_backlogs=True,
            )

        bc = submit_branch_change(
            student_id="24BCS205",
            current_branch="ECE",
            preferred_branch_1="CSE",
            preferred_branch_2="DSAI",
            current_cpi=Decimal("9.10"),
            credits_completed=44,
            has_backlogs=False,
        )
        self.assertEqual(bc.status, BranchChangeStatus.SUBMITTED)

        # Duplicate submission refused
        with self.assertRaises(OAPDomainError):
            submit_branch_change(
                student_id="24BCS205",
                current_branch="ECE",
                preferred_branch_1="CSE",
                current_cpi=Decimal("9.10"),
            )

        verified = verify_branch_change(bc.pk)
        self.assertTrue(verified)

        allocate_and_sanction(bc.pk, allocated_branch="CSE", approved_by="DEAN_ACAD")
        bc.refresh_from_db()
        self.assertEqual(bc.status, BranchChangeStatus.APPROVED)
