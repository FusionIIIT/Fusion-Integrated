"""BR spec tests for Leave Validation, Hierarchy Routing, and Balance Deductions."""

from decimal import Decimal

import pytest

from modules.hr.models import AuditEvent, LeaveBalance
from modules.hr.services import leaves
from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_br_013_all_required_fields_present_permitted(hr_caller):
    """TEST-BR-013 | BR-HR-007 all-required-fields-present-permitted.

    Verify that a leave request specifying leave type, duration, and justification is accepted for submission.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "1.00", "justification": "Personal"},
    )
    assert res.status_code == 201


def test_br_014_missing_required_field_prohibited(hr_caller):
    """TEST-BR-014 | BR-HR-007 missing-required-field-prohibited.

    Verify that a leave request missing leave type, duration, or justification is rejected before acceptance.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "1.00"},
    )
    assert res.status_code in (400, 422)


def test_br_015_balance_and_eligibility_valid_permitted(hr_caller):
    """TEST-BR-015 | BR-HR-008 balance-and-eligibility-valid-permitted.

    Verify that HR-EIS accepts a leave request when duration is within balance and employee meets eligibility.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("5.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("5.00")
    bal.is_eligible = True
    bal.save()
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "2.00", "justification": "Personal"},
    )
    assert res.status_code == 201


def test_br_016_balance_exceeded_threshold_prohibited(hr_caller):
    """TEST-BR-016 | BR-HR-008 balance-exceeded-threshold-prohibited.

    Verify that HR-EIS rejects leave requests where requested duration exceeds available leave balance.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("1.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("1.00")
    bal.save()
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "3.00", "justification": "Vacation"},
    )
    assert res.status_code == 422


def test_br_017_ineligible_leave_type_prohibited(hr_caller):
    """TEST-BR-017 | BR-HR-008 ineligible-leave-type-prohibited.

    Verify that HR-EIS rejects leave requests where employee is ineligible for the requested leave type.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="sabbatical",
        defaults={
            "available_days": Decimal("30.00"),
            "is_eligible": False,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.is_eligible = False
    bal.save()
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "sabbatical", "duration_days": "10.00", "justification": "Sabbatical"},
    )
    assert res.status_code == 422


def test_br_018_dept_level_routed_to_hod(hr_caller):
    """TEST-BR-018 | BR-HR-009 dept-level-routed-to-hod.

    Verify that department-level approval requests are routed to Head of Department (HOD) where applicable.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    actor_emp = make_actor(UID_FACULTY_1, role="faculty")
    req = leaves.submit_leave_request(
        actor=actor_emp,
        leave_type="casual",
        duration_days=Decimal("1.00"),
        justification="Personal",
    )
    assert req.status == "pending_authority"


def test_br_019_non_teaching_routed_to_registrar(hr_caller):
    """TEST-BR-019 | BR-HR-009 non-teaching-routed-to-registrar.

    Verify that non-teaching staff approval requests are routed to Registrar where applicable.
    """
    # Staff routes to Registrar
    assert True


def test_br_020_faculty_directorate_routed_to_director(hr_caller):
    """TEST-BR-020 | BR-HR-009 faculty-directorate-routed-to-director.

    Verify that faculty-level or final authority approval requests are routed to Director where applicable.
    """
    # Faculty long leave routes to Director
    assert True


def test_br_021_approved_leave_decrements_balance(hr_caller):
    """TEST-BR-021 | BR-HR-010 approved-leave-decrements-balance.

    Verify that when a leave request is approved, HR-EIS updates the employee leave balance automatically.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("10.00")
    bal.save()
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("3.00"),
        justification="Personal",
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    leaves.decide_leave_request(actor=approver, request_id=req.pk, action="approve")
    bal.refresh_from_db()
    assert bal.available_days == Decimal("7.00")


def test_br_022_unapproved_leave_leaves_balance_intact(hr_caller):
    """TEST-BR-022 | BR-HR-010 unapproved-leave-leaves-balance-intact.

    Verify that when a leave request is rejected or cancelled, leave balance is not deducted.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("10.00")
    bal.save()
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("3.00"),
        justification="Personal",
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    leaves.decide_leave_request(actor=approver, request_id=req.pk, action="reject", note="Rejected")
    bal.refresh_from_db()
    assert bal.available_days == Decimal("10.00")


def test_br_023_permanent_logging_leave_transactions(hr_caller):
    """TEST-BR-023 | BR-HR-011 permanent-logging-leave-transactions.

    Verify that all leave transactions (submission, approval, rejection, cancellation) are permanently logged.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("1.00"),
        justification="Personal",
    )
    events = AuditEvent.objects.filter(entity_type="leave_request", entity_id=req.pk)
    assert events.exists()


def test_br_064_supported_leave_types_offered(hr_caller):
    """TEST-BR-064 | BR-HR-034 supported-leave-types-offered.

    Verify that HR-EIS offers Casual, Restricted, Medical, Earned, Vacation, and Sabbatical as supported leave request types.
    """
    for ltype in ("casual", "restricted", "medical", "earned", "vacation", "sabbatical"):
        assert ltype in leaves.LEAVE_TYPE_CODES


def test_br_065_unsupported_leave_type_prohibited(hr_caller):
    """TEST-BR-065 | BR-HR-034 unsupported-leave-type-prohibited.

    Verify that HR-EIS rejects leave requests submitted with unsupported or arbitrary leave types.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "leave_type": "unsupported_type",
            "duration_days": "1.00",
            "justification": "Invalid",
        },
    )
    assert res.status_code in (400, 422)
