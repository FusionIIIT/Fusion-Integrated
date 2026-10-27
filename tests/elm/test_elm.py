
import pytest
from datetime import date

from modules.elm.services import ELMService
from modules.elm.selectors import ELMSellector
from modules.elm.domain.entities import (
    EmployeeProfile,
    LeaveApplication,
    LeaveType,
)
from modules.elm.domain.rules import calculate_entitlement


@pytest.fixture(scope="module")
def mock_selectors():
    """Mock selector methods to isolate service logic during tests."""

    original_get_employee = ELMSellector.get_employee
    original_get_applications = ELMSellector.get_applications_by_employee
    original_get_application = getattr(ELMSellector, "get_application", None)
    original_update_status = getattr(
        ELMSellector, "update_application_status", None
    )

    if hasattr(ELMSellector, "_application_store"):
        ELMSellector._application_store = {}

    if hasattr(ELMSellector, "_next_application_id"):
        ELMSellector._next_application_id = 1

    def mock_get_employee(emp_id):
        return EmployeeProfile(
            employee_id=emp_id,
            roles={"ACT-01_Faculty"},
            name="Test User",
            org_unit="CS",
        )

    def mock_get_applications(emp_id):
        return []

    ELMSellector.get_employee = mock_get_employee
    ELMSellector.get_applications_by_employee = mock_get_applications

    yield

    ELMSellector.get_employee = original_get_employee
    ELMSellector.get_applications_by_employee = original_get_applications

    if original_get_application is not None:
        ELMSellector.get_application = original_get_application

    if original_update_status is not None:
        ELMSellector.update_application_status = original_update_status


def test_submit_leave_application_success(mock_selectors):
    """Tests successful leave application submission."""

    service = ELMService("user_123")

    application_data = {
        "leave_type": "CL",
        "start_date": date(2024, 10, 1),
        "end_date": date(2024, 10, 3),
    }

    application = service.submit_leave_application(application_data)

    assert application.status == "PENDING"
    assert application.employee_id == "user_123"
    assert application.application_id is not None

def test_submit_leave_application_insufficient_entitlement(
    mock_selectors, monkeypatch
):
    import modules.elm.services as services_module

    monkeypatch.setattr(
        services_module,
        "calculate_entitlement",
        lambda employee, leave_type: 0.0,
    )

    service = ELMService("user_123")
    application_data = {
        "leave_type": "CL",
        "start_date": date(2024, 10, 1),
        "end_date": date(2024, 10, 3),
    }

    with pytest.raises(ValueError, match="entitlement is zero"):
        service.submit_leave_application(application_data)

def test_submit_leave_application_overlap_exists(mock_selectors):
    """Tests rejection of leave overlapping with existing approved leave."""

    auth_user_id = "user_123"
    service = ELMService(auth_user_id)

    existing_app = LeaveApplication(
        application_id=1,
        employee_id=auth_user_id,
        leave_type=LeaveType(
            code="CL",
            name="CL",
            description="",
            allows_carry_forward=False,
            is_restricted=False,
        ),
        start_date=date(2024, 9, 25),
        end_date=date(2024, 10, 5),
        status="APPROVED",
    )

    ELMSellector.get_applications_by_employee = (
        lambda emp_id: [existing_app]
    )

    application_data = {
        "leave_type": "CL",
        "start_date": date(2024, 10, 1),
        "end_date": date(2024, 10, 3),
    }

    with pytest.raises(ValueError) as excinfo:
        service.submit_leave_application(application_data)

    assert "overlap" in str(excinfo.value).lower()


def test_review_and_approve_request_success(mock_selectors,monkeypatch):
    """Tests approval of a pending leave application."""

    service = ELMService(auth_user_id="approver_123")
    monkeypatch.setattr(
    service,
    "_get_allowed_actors",
    lambda application: {"approver_123"},
)

    app = LeaveApplication(
        application_id=100,
        employee_id="user_123",
        leave_type=LeaveType(
            code="CL",
            name="CL",
            description="",
            allows_carry_forward=False,
            is_restricted=False,
        ),
        start_date=date(2024, 10, 1),
        end_date=date(2024, 10, 3),
        status="PENDING",
    )

    ELMSellector.get_application = lambda app_id: app

    def update_application_status(app_id, status):
        app.status = status

    ELMSellector.update_application_status = update_application_status

    approved_app = service.review_and_approve_request(
        100, "approver_123"
    )

    assert approved_app.status == "APPROVED"


def test_calculate_el_entitlement_limitation(mock_selectors):
    """Documents the current hardcoded EL entitlement limitation."""

    employee = EmployeeProfile(
        employee_id="test_el",
        roles=set(),
        name="EL Test",
        org_unit="Test",
    )

    leave_type = LeaveType(
        code="EL",
        name="Earned Leave",
        description="Earned Leave",
        allows_carry_forward=True,
        is_restricted=False,
    )

    entitlement = calculate_entitlement(employee, leave_type)

    # Documents current behavior, not a confirmed business requirement.
    assert entitlement == 18.0
