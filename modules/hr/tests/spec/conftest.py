"""Shared test fixtures and helpers for HR specification-based tests."""

from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.principal import Principal
from modules.hr.models import EmployeeRecord, LeaveBalance, WorkflowRoute
from modules.hr.registry import ROLE_GRANTS
from modules.hr.services import appraisals, configuration, employees, notifications

# Standard test identities
UID_HR_ADMIN = 7
UID_FACULTY_1 = 1001
UID_FACULTY_2 = 1002
UID_STAFF_1 = 2001
UID_STAFF_2 = 2002
UID_HOD = 88
UID_REGISTRAR = 99
UID_DIRECTOR = 100
UID_ACCOUNTANT = 101
UID_UNAUTHORIZED = 9999

VALID_DRIVE_LINK = "https://drive.google.com/file/d/1A2b3C4d5E6f7G8h9I0j1K2l3M4n5O6p7Q8r9S0t/view"


@pytest.fixture(autouse=True)
def mock_hr_directory(monkeypatch):
    """Ensure directory service recognizes test employees without external calls."""
    people = {
        UID_HR_ADMIN: SimpleNamespace(
            user_id=UID_HR_ADMIN, kind="staff", email="hr@test.edu", full_name="HR Admin"
        ),
        UID_FACULTY_1: SimpleNamespace(
            user_id=UID_FACULTY_1, kind="faculty", email="fac1@test.edu", full_name="Faculty One"
        ),
        UID_FACULTY_2: SimpleNamespace(
            user_id=UID_FACULTY_2, kind="faculty", email="fac2@test.edu", full_name="Faculty Two"
        ),
        UID_STAFF_1: SimpleNamespace(
            user_id=UID_STAFF_1, kind="staff", email="staff1@test.edu", full_name="Staff One"
        ),
        UID_STAFF_2: SimpleNamespace(
            user_id=UID_STAFF_2, kind="staff", email="staff2@test.edu", full_name="Staff Two"
        ),
        UID_HOD: SimpleNamespace(
            user_id=UID_HOD, kind="faculty", email="hod@test.edu", full_name="Head of Dept"
        ),
        UID_REGISTRAR: SimpleNamespace(
            user_id=UID_REGISTRAR, kind="staff", email="reg@test.edu", full_name="Registrar"
        ),
        UID_DIRECTOR: SimpleNamespace(
            user_id=UID_DIRECTOR, kind="faculty", email="dir@test.edu", full_name="Director"
        ),
        UID_ACCOUNTANT: SimpleNamespace(
            user_id=UID_ACCOUNTANT, kind="staff", email="acc@test.edu", full_name="Accountant"
        ),
    }
    active_ids = set(people)

    for service in (employees, configuration, appraisals, notifications):
        monkeypatch.setattr(
            service.directory,
            "get_users",
            lambda user_ids, p=people: {uid: p[uid] for uid in user_ids if uid in p},
        )
        monkeypatch.setattr(
            service.directory,
            "held_employee_ids",
            lambda ids=active_ids: set(ids),
        )
    return people


@pytest.fixture
def hr_caller(stub_iam):
    """Authenticated API call helper for HR spec tests."""
    client = APIClient()
    req_counter = 0

    def _call(
        method: str,
        path: str,
        *,
        user_id: int = UID_HR_ADMIN,
        role: str = "hr_officer",
        kind: str = "staff",
        permissions: tuple[str, ...] | None = None,
        modules: tuple[str, ...] = ("hr",),
        data=None,
        content_type="application/json",
    ):
        nonlocal req_counter
        req_counter += 1
        effective_permissions = (
            permissions if permissions is not None else tuple(ROLE_GRANTS.get(role, ()))
        )
        session = make_session(
            user_id=user_id,
            kind=kind,
            modules=modules,
            permissions=effective_permissions,
            roles=(role,),
            active_role=role,
        )
        stub_iam(session, users={})
        client.credentials(HTTP_AUTHORIZATION=f"Token spec-test-token-{req_counter}")
        operation = getattr(client, method.lower())
        if data is not None:
            return operation(path, data=data, format="json")
        return operation(path)

    return _call


def make_actor(
    user_id: int,
    role: str = "faculty",
    kind: str = "faculty",
    permissions: tuple[str, ...] | None = None,
    modules: tuple[str, ...] = ("hr",),
) -> Principal:
    """Create an authenticated Principal with specified HR role/permissions."""
    effective_permissions = (
        permissions if permissions is not None else tuple(ROLE_GRANTS.get(role, ()))
    )
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind=kind,
            permissions=effective_permissions,
            modules=modules,
            roles=(role,),
            active_role=role,
        )
    )


def ensure_employee(
    user_id: int, kind: str = "faculty", department: str = "CSE", designation: str = "Professor"
) -> EmployeeRecord:
    """Ensure an employee record exists in DB for tests."""
    record, _ = EmployeeRecord.objects.get_or_create(
        user_id=user_id,
        defaults={
            "employee_category": kind,
            "department": department,
            "designation": designation,
            "created_by_user_id": UID_HR_ADMIN,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    return record


def ensure_workflow_route(
    employee_category: str,
    request_type: str,
    steps: list | None = None,
) -> WorkflowRoute:
    """Ensure a WorkflowRoute exists so leave/claim submission can proceed.

    Default single-step route uses UID_HOD as the approver.
    """
    if steps is None:
        steps = [{"approver_user_id": UID_HOD, "label": "HOD"}]
    route, _ = WorkflowRoute.objects.get_or_create(
        employee_category=employee_category,
        request_type=request_type,
        defaults={
            "steps": steps,
            "reminder_after_hours": 24,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    return route


def ensure_leave_balance(
    employee_user_id: int,
    leave_type: str = "casual",
    available_days="10.00",
    is_eligible: bool = True,
) -> LeaveBalance:
    """Ensure a leave balance exists for the given employee."""
    from decimal import Decimal

    emp = ensure_employee(employee_user_id)
    bal, _ = LeaveBalance.objects.get_or_create(
        employee=emp,
        leave_type=leave_type,
        defaults={
            "available_days": Decimal(str(available_days)),
            "is_eligible": is_eligible,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    return bal
