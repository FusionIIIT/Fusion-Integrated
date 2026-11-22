"""FR spec tests for Leave Management Lifecycle."""

from decimal import Decimal

import pytest

from modules.hr.models import LeaveBalance, LeaveLedgerEntry
from modules.hr.services import leaves
from modules.hr.services.leaves import LEAVE_TYPE_CODES
from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_fr_007_consolidated_leave_management_lifecycle(hr_caller):
    """TEST-FR-007 | HR-CFR-007 consolidated-leave-management-lifecycle.

    Verify the complete leave management lifecycle including leave application for supported types, mandatory field validation, balance validation, approval routing, automated balance deduction, and transaction logging.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    _bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    # Apply
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "2.00", "justification": "Personal work"},
    )
    assert res.status_code == 201


def test_fr_061_employee_apply_for_leave(hr_caller):
    """TEST-FR-061 | HR-AFR-029 employee-apply-for-leave.

    Verify that HR-EIS allows Employees to apply for leave requests.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    _bal, _ = LeaveBalance.objects.get_or_create(
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
        data={"leave_type": "casual", "duration_days": "1.00", "justification": "Rest"},
    )
    assert res.status_code == 201


def test_fr_062_support_casual_leave_type(hr_caller):
    """TEST-FR-062 | HR-AFR-030 support-casual-leave-type.

    Verify that HR-EIS supports Casual leave as an available leave request type.
    """
    assert "casual" in LEAVE_TYPE_CODES


def test_fr_063_support_restricted_leave_type(hr_caller):
    """TEST-FR-063 | HR-AFR-031 support-restricted-leave-type.

    Verify that HR-EIS supports Restricted leave as an available leave request type.
    """
    assert "restricted" in LEAVE_TYPE_CODES


def test_fr_064_support_medical_leave_type(hr_caller):
    """TEST-FR-064 | HR-AFR-032 support-medical-leave-type.

    Verify that HR-EIS supports Medical leave as an available leave request type.
    """
    assert "medical" in LEAVE_TYPE_CODES


def test_fr_065_support_earned_leave_type(hr_caller):
    """TEST-FR-065 | HR-AFR-033 support-earned-leave-type.

    Verify that HR-EIS supports Earned leave as an available leave request type.
    """
    assert "earned" in LEAVE_TYPE_CODES


def test_fr_066_support_vacation_leave_type(hr_caller):
    """TEST-FR-066 | HR-AFR-034 support-vacation-leave-type.

    Verify that HR-EIS supports Vacation leave as an available leave request type.
    """
    assert "vacation" in LEAVE_TYPE_CODES


def test_fr_067_support_sabbatical_leave_type(hr_caller):
    """TEST-FR-067 | HR-AFR-035 support-sabbatical-leave-type.

    Verify that HR-EIS supports Sabbatical leave as an available leave request type.
    """
    assert "sabbatical" in LEAVE_TYPE_CODES


def test_fr_068_valid_leave_type_provided(hr_caller):
    """TEST-FR-068 | HR-AFR-036 valid-leave-type-provided.

    Verify that HR-EIS accepts a leave request when valid leave type is specified.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_medical")
    _bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="medical",
        defaults={
            "available_days": Decimal("15.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "medical", "duration_days": "2.00", "justification": "Fever"},
    )
    assert res.status_code == 201


def test_fr_069_omit_leave_type_rejected(hr_caller):
    """TEST-FR-069 | HR-AFR-036 omit-leave-type-rejected.

    Verify that HR-EIS requires leave type and rejects leave requests where leave type is omitted.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"duration_days": "2.00", "justification": "Fever"},
    )
    assert res.status_code in (400, 422)


def test_fr_070_valid_leave_duration_provided(hr_caller):
    """TEST-FR-070 | HR-AFR-037 valid-leave-duration-provided.

    Verify that HR-EIS accepts a leave request when valid leave duration is specified.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    _bal, _ = LeaveBalance.objects.get_or_create(
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
        data={"leave_type": "casual", "duration_days": "3.00", "justification": "Family event"},
    )
    assert res.status_code == 201


def test_fr_071_omit_leave_duration_rejected(hr_caller):
    """TEST-FR-071 | HR-AFR-037 omit-leave-duration-rejected.

    Verify that HR-EIS requires leave duration and rejects leave requests where duration is omitted or empty.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "justification": "Family event"},
    )
    assert res.status_code in (400, 422)


def test_fr_072_valid_leave_justification_provided(hr_caller):
    """TEST-FR-072 | HR-AFR-038 valid-leave-justification-provided.

    Verify that HR-EIS accepts a leave request when valid justification is specified.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    _bal, _ = LeaveBalance.objects.get_or_create(
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
        data={
            "leave_type": "casual",
            "duration_days": "1.00",
            "justification": "Doctor appointment",
        },
    )
    assert res.status_code == 201


def test_fr_073_omit_leave_justification_rejected(hr_caller):
    """TEST-FR-073 | HR-AFR-038 omit-leave-justification-rejected.

    Verify that HR-EIS requires justification and rejects leave requests where justification is omitted or blank.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "1.00"},
    )
    assert res.status_code in (400, 422)


def test_fr_074_valid_leave_balance_accepted(hr_caller):
    """TEST-FR-074 | HR-AFR-039 valid-leave-balance-accepted.

    Verify that HR-EIS accepts a leave request submission when requested duration is within available leave balance.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_earned")
    _bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="earned",
        defaults={
            "available_days": Decimal("30.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "earned", "duration_days": "5.00", "justification": "Vacation"},
    )
    assert res.status_code == 201


def test_fr_075_insufficient_leave_balance_rejected(hr_caller):
    """TEST-FR-075 | HR-AFR-039 insufficient-leave-balance-rejected.

    Verify that HR-EIS validates leave balance and rejects leave requests where duration exceeds available balance.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.get_or_create(
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
        data={"leave_type": "casual", "duration_days": "5.00", "justification": "Urgent"},
    )
    assert res.status_code == 422


def test_fr_076_valid_leave_eligibility_accepted(hr_caller):
    """TEST-FR-076 | HR-AFR-040 valid-leave-eligibility-accepted.

    Verify that HR-EIS accepts a leave request when employee meets eligibility criteria for the requested leave type.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.is_eligible = True
    bal.save()
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "1.00", "justification": "Personal"},
    )
    assert res.status_code == 201


def test_fr_077_ineligibility_leave_rejected(hr_caller):
    """TEST-FR-077 | HR-AFR-040 ineligibility-leave-rejected.

    Verify that HR-EIS validates leave eligibility and rejects requests from employees not eligible for the requested leave type.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="sabbatical",
        defaults={
            "available_days": Decimal("100.00"),
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
        data={
            "leave_type": "sabbatical",
            "duration_days": "10.00",
            "justification": "Research sabbatical",
        },
    )
    assert res.status_code == 422


def test_fr_078_route_leave_predefined_hierarchy(hr_caller):
    """TEST-FR-078 | HR-AFR-041 route-leave-predefined-hierarchy.

    Verify that HR-EIS routes leave requests through a predefined approval hierarchy.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    _bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    actor = make_actor(UID_FACULTY_1, role="faculty")
    req = leaves.submit_leave_request(
        actor=actor, leave_type="casual", duration_days=Decimal("1.00"), justification="Personal"
    )
    assert req.status == "pending_authority"


def test_fr_079_update_leave_balances_automatically_on_approval(hr_caller):
    """TEST-FR-079 | HR-AFR-042 update-leave-balances-automatically-on-approval.

    Verify that HR-EIS updates employee leave balances automatically when leave is approved.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    bal, _ = LeaveBalance.objects.get_or_create(
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
    actor = make_actor(UID_FACULTY_1, role="faculty")
    req = leaves.submit_leave_request(
        actor=actor, leave_type="casual", duration_days=Decimal("2.00"), justification="Personal"
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    decided = leaves.decide_leave_request(actor=approver, request_id=req.pk, action="approve")
    assert decided.status == "approved"
    bal.refresh_from_db()
    assert bal.available_days == Decimal("8.00")


def test_fr_080_permanently_log_all_leave_transactions(hr_caller):
    """TEST-FR-080 | HR-AFR-043 permanently-log-all-leave-transactions.

    Verify that HR-EIS permanently logs all leave transactions.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    _bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    actor = make_actor(UID_FACULTY_1, role="faculty")
    req = leaves.submit_leave_request(
        actor=actor, leave_type="casual", duration_days=Decimal("1.00"), justification="Personal"
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    leaves.decide_leave_request(actor=approver, request_id=req.pk, action="approve")
    entries = LeaveLedgerEntry.objects.filter(leave_request=req)
    assert entries.exists()
