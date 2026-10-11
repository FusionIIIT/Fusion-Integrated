import pytest
from modules.elm.services import ELMService
from modules.elm.selectors import ELMSellector
from modules.elm.domain.entities import LeaveApplication, LeaveType, EmployeeProfile
from modules.elm.domain.rules import calculate_entitlement, check_overlap
from modules.elm.contracts import ELMContracts
from datetime import date

# Mocking the Selector layer dependencies to isolate service logic
@pytest.fixture(scope="module")
def mock_selectors():
    # Reset the state of the selector store before each test module run
    ELMSellector._application_store = {}
    ELMSellector._next_application_id = 1

    # Store original methods
    ELMSellector.get_employee.__original__ = ELMSellector.get_employee
    ELMSellector.get_applications_by_employee.__original__ = ELMSellector.get_applications_by_employee

    # Ensure mock functions behave as expected
    def mock_get_employee(emp_id):
        return EmployeeProfile(employee_id=emp_id, roles={"ACT-01_Faculty"}, name="Test User", org_unit="CS")
    
    def mock_get_applications(emp_id):
        return []
        
    # Replace static methods for testing isolation
    ELMSellector.get_employee = mock_get_employee
    ELMSellector.get_applications_by_employee = mock_get_applications
    
    yield # Yield control to the test functions
    
    # Teardown
    ELMSellector.get_employee = ELMSellector.get_employee.__original__
    ELMSellector.get_applications_by_employee = ELMSellector.get_applications_by_employee.__original__


def test_submit_leave_application_success(mock_selectors):
    """Tests a successful leave application submission."""
    auth_user_id = "user_123"
    service = ELMService(auth_user_id)

    application_data = {
        'leave_type': 'CL',
        'start_date': date(2024, 10, 1),
        'end_date': date(2024, 10, 3)
    }
    
    try:
        # Note: We must ensure calculate_entitlement succeeds here for the test to pass.
        application = service.submit_leave_application(application_data)
        
        assert application.status == 'PENDING'
        assert application.employee_id == auth_user_id
        assert application.application_id is not None
        
    except Exception as e:
        pytest.fail(f"Submission failed unexpectedly: {e}")
def test_submit_leave_application_insufficient_entitlement(mock_selectors):
    """Tests failure when employee does not have enough leave balance."""
    auth_user_id = "user_123"
    service = ELMService(auth_user_id)

    application_data = {
        'leave_type': 'CL',
        'start_date': date(2024, 10, 1),
        'end_date': date(2024, 10, 3)
    }
    
    # Simulating an Entitlement Failure Scenario
    # The test relies on the implementation in domain/rules.py to raise ValueError
    # when entitlement is zero.
    with pytest.raises(ValueError) as excinfo:
        service.submit_leave_application(application_data) 
        
    assert "entitlement is zero" in str(excinfo.value) or "invalid" in str(excinfo.value)


def test_submit_leave_application_overlap_exists(mock_selectors):
    """Tests failure when the requested leave overlaps with existing approved leave."""
    auth_user_id = "user_123"
    service = ELMService(auth_user_id)
    
    # Setup existing application that causes overlap
    existing_app = LeaveApplication(
        application_id=1,
        employee_id=auth_user_id,
        leave_type=LeaveType(code='CL', name='CL', description='', allows_carry_forward=False, is_restricted=False),
        start_date=date(2024, 9, 25), # Existing leave starts near the test period
        end_date=date(2024, 10, 5), # Existing leave overlaps the test period (2024, 10, 1 to 2024, 10, 3)
        status='APPROVED'
    )

    # Set the mock selector to return the existing overlapping application
    ELMSellector.get_applications_by_employee = lambda emp_id: [existing_app]
    ELMSellector.get_applications_by_employee = lambda emp_id: [existing_app]
    )
    
    # Set the mock selector to return the existing overlapping application
    ELMSellector.get_applications_by_employee = lambda emp_id: [existing_app]

    application_data = {
        'leave_type': 'CL',
        'start_date': date(2024, 10, 1),
    assert "overlaps with existing approved leave" in str(excinfo.value)
        'end_date': date(2024, 10, 3)
    assert "overlaps with existing approved leave" in str(excinfo.value)
    }

    with pytest.raises(ValueError) as excinfo:
        service.submit_leave_application(application_data)
        
    assert "overlaps with existing approved leave" in str(excinfo.value)

# Add a simple test for approval flow
def test_review_and_approve_request_success(mock_selectors):
    """Tests the successful approval of a pending application."""
    service = ELMService(auth_user_id="approver_123")
    
    # Create a mock application
    app = LeaveApplication(
    )

    # Ensure Selector returns our mock app
    ELMSellector.get_application = lambda app_id: app
        application_id=100,
        employee_id="user_123",
    )

    # Ensure Selector returns our mock app
    ELMSellector.get_application = lambda app_id: app
    
    # Mock the update method call
    ELMSellector.update_application_status = lambda app_id, status: None
    ELMSellector.get_application = lambda app_id: app
    approved_app = service.review_and_approve_request(100, "approver_123")
    assert approved_app.status == 'APPROVED'
        leave_type=LeaveType(code='CL', name='CL', description='', allows_carry_forward=False, is_restricted=False),
        start_date=date(2024, 10, 1),
        end_date=date(2024, 10, 3),
        status='PENDING'
    )
    )
    
    # Ensure Selector returns our mock app
    ELMSellector.get_application = lambda app_id: app
    
    # Mock the update method call
    ELMSellector.update_application_status = lambda app_id, status: None
    
    approved_app = service.review_and_approve_request(100, "approver_123")
    
    assert approved_app.status == 'APPROVED'
