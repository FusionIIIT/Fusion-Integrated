"""Pure business rule validations for HR-EIS."""
import datetime
from modules.hr_eis.contracts import LeaveTypes, EmploymentTypes

class DomainValidationError(Exception):
    pass

def validate_leave_request(available_balance, requested_days, leave_type, employment_type, years_of_service=1):
    """Enforces BR-HR-007, BR-HR-008, BR-HR-034."""
    if leave_type not in LeaveTypes.ALL:
        raise DomainValidationError(f"Invalid leave type: {leave_type}. Must be one of {LeaveTypes.ALL}.")
    if requested_days <= 0:
        raise DomainValidationError("Requested leave duration must be strictly positive.")
    if requested_days > available_balance:
        raise DomainValidationError(f"Insufficient leave balance: requested {requested_days}, available {available_balance}.")
    if leave_type == LeaveTypes.SABBATICAL:
        if employment_type != EmploymentTypes.FACULTY:
            raise DomainValidationError("Sabbatical leave is restricted exclusively to Faculty members.")
        if years_of_service < 3:
            raise DomainValidationError("Sabbatical leave requires at least 3 years of continuous service.")
    if leave_type == LeaveTypes.VACATION and employment_type != EmploymentTypes.FACULTY:
        raise DomainValidationError("Vacation leave is applicable only to academic faculty staff.")
    return True

def validate_appraisal_window(is_open, current_date, deadline):
    """Enforces BR-HR-012."""
    if not is_open:
        raise DomainValidationError("Appraisal submission is rejected: appraisal cycle window is currently closed.")
    if current_date > deadline:
        raise DomainValidationError(f"Appraisal submission rejected: deadline {deadline} has elapsed (current date: {current_date}).")
    return True

def validate_ltc_claim(claim_type, estimated_amount, claimed_amount=None):
    """Enforces BR-HR-016, BR-HR-020."""
    if estimated_amount <= 0:
        raise DomainValidationError("LTC estimated amount must be strictly greater than 0.")
    if claimed_amount is not None and claimed_amount <= 0:
        raise DomainValidationError("LTC claimed amount must be strictly greater than 0.")
    return True

def validate_cpda_claim(amount, purpose, available_budget):
    """Enforces BR-HR-020, BR-HR-021."""
    if amount <= 0:
        raise DomainValidationError("CPDA claim amount must be strictly positive.")
    if not purpose or len(purpose.strip()) < 5:
        raise DomainValidationError("CPDA claim must provide a clear valid academic purpose.")
    if amount > available_budget:
        raise DomainValidationError(f"CPDA claim exceeds available allocated budget ({available_budget}).")
    return True

def validate_settlement(claim_status, approved_amount, disbursement_ref):
    """Enforces BR-HR-019, BR-HR-022, BR-HR-035."""
    from modules.hr_eis.contracts import ClaimStatus
    if claim_status != ClaimStatus.APPROVED_AUTHORITY:
        raise DomainValidationError("Only authority-approved claims can be processed for financial settlement.")
    if approved_amount <= 0:
        raise DomainValidationError("Approved amount must be positive for settlement.")
    if not disbursement_ref or not disbursement_ref.strip():
        raise DomainValidationError("A valid disbursement reference / transaction ID is mandatory before financial commit.")
    return True
