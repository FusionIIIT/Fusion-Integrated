import pytest
from modules.hr_eis.contracts import LeaveTypes, EmploymentTypes, LeaveStatus, ClaimStatus, AuthorityRoles
from modules.hr_eis.domain.rules import validate_leave_request, validate_appraisal_window, validate_ltc_claim, validate_cpda_claim, validate_settlement, DomainValidationError
from modules.hr_eis.domain.state_machine import LeaveStateMachine, AppraisalStateMachine, ClaimStateMachine, InvalidStateTransitionError
import datetime

def test_leave_request_valid():
    assert validate_leave_request(10.0, 3.0, LeaveTypes.CASUAL, EmploymentTypes.FACULTY) is True

def test_leave_insufficient_balance():
    with pytest.raises(DomainValidationError):
        validate_leave_request(2.0, 5.0, LeaveTypes.CASUAL, EmploymentTypes.FACULTY)

def test_sabbatical_faculty_only():
    with pytest.raises(DomainValidationError):
        validate_leave_request(20.0, 5.0, LeaveTypes.SABBATICAL, EmploymentTypes.STAFF, years_of_service=5)

def test_sabbatical_years_of_service():
    with pytest.raises(DomainValidationError):
        validate_leave_request(20.0, 5.0, LeaveTypes.SABBATICAL, EmploymentTypes.FACULTY, years_of_service=1)

def test_appraisal_window():
    today = datetime.date.today()
    future = today + datetime.timedelta(days=10)
    past = today - datetime.timedelta(days=10)
    assert validate_appraisal_window(True, today, future) is True
    with pytest.raises(DomainValidationError):
        validate_appraisal_window(False, today, future)
    with pytest.raises(DomainValidationError):
        validate_appraisal_window(True, today, past)

def test_claim_settlement():
    assert validate_settlement(ClaimStatus.APPROVED_AUTHORITY, 5000.0, "DISB_123") is True
    with pytest.raises(DomainValidationError):
        validate_settlement(ClaimStatus.SUBMITTED, 5000.0, "DISB_123")
