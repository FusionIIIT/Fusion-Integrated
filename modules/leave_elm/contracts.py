from collections.abc import Sequence
from dataclasses import dataclass

from modules.leave_elm.selectors.leave import (
    get_all_applications,
    get_applications_for_employee,
    get_employee_balance,
)
from modules.leave_elm.services.leave import (
    apply_leave,
    approve_application,
    update_substitute_response,
)

"""
Public interface functions exposed by the Employee Leave Management (ELM) module.

This module serves as the contract for other platform modules (e.g., UI rendering,
other services) to interact with ELM data without having direct Django/DRF dependencies.

Dependencies are assumed to be implemented in domain/, selectors/, and services/..
"""


# ==============================================================================
# DATA TRANSFER OBJECTS (DTOs) - THE CONTRACTS
# ==============================================================================


@dataclass
class LeaveBalanceDTO:
    """DTO representing an employee's leave balance."""

    available_balance: float
    annual_entitlement: float


@dataclass
class LeaveApplicationSummaryDTO:
    """DTO summarizing a submitted leave application."""

    id: int
    employee_id: str
    category: str
    start_date: str
    end_date: str
    reason: str
    status: str
    substitute_id: str | None


@dataclass
class SubstituteResponseDTO:
    """DTO for a substitute's acceptance or declination."""

    application_id: int
    substitute_id: str
    response_status: str  # e.g., 'accepted', 'declined', 'pending'
    notes: str | None


@dataclass
class LeaveReportDTO:
    """Comprehensive report summary for reporting/admin views."""

    employee_id: str
    total_leave_days_used: float
    total_leave_days_available: float
    recent_applications: list[LeaveApplicationSummaryDTO]
    balance_by_category: dict[str, LeaveBalanceDTO]


# ==============================================================================
# API INTERFACE FUNCTIONS (STUBS)
# ==============================================================================


# --- Balance Operations ---


def get_employee_balance_contract(
    employee_ids: Sequence[str], category: str = "EL"
) -> dict[str, LeaveBalanceDTO]:
    """
    Retrieves current leave balances for a sequence of employee IDs and category.

    :param employee_ids: Sequence of employee ID strings.
    :param category: The leave category code (e.g., 'EL', 'CL', 'SCL').
    :return: Dictionary mapping employee_id to LeaveBalanceDTO.
    """
    results = {}
    for employee_id in employee_ids:
        balance_data = get_employee_balance(employee_id, category) or {}
        results[employee_id] = LeaveBalanceDTO(
            available_balance=balance_data.get("available_balance", 0.0),
            annual_entitlement=balance_data.get("annual_entitlement", 0.0),
        )
    return results


def get_all_balances_contract(employee_ids: Sequence[str]) -> dict[str, dict[str, LeaveBalanceDTO]]:
    """
    Retrieves balances for a sequence of employees and categories.

    NOTE: Accepts a sequence (list/tuple) of employee IDs to prevent N+1 queries.
    Each employee_id must be paired with each category in the result structure.

    :param employee_ids: Sequence of employee ID strings.
    :return: Dictionary mapping employee_id -> {category -> LeaveBalanceDTO}.
    """
    # Placeholder for bulk balance fetching logic - returns empty dict until backend integrated
    return {}


# --- Application Operations ---


def submit_new_leave_application_contract(
    employee_id: str,
    category: str,
    start_date: str,
    end_date: str,
    reason: str,
    substitute_id: str | None = None,
    is_station_leave: bool = False,
) -> LeaveApplicationSummaryDTO:
    """
    Submits a new leave application request.

    :param employee_id: The ID of the applicant.
    :param category: The leave category code.
    :param start_date: Start date (YYYY-MM-DD).
    :param end_date: End date (YYYY-MM-DD).
    :param reason: The reason for leave.
    :param substitute_id: Optional ID of nominated substitute.
    :param is_station_leave: Flag indicating station leave.
    :return: LeaveApplicationSummaryDTO containing the new application ID and status.
    """
    # Calls the service layer to perform the mutation
    result = apply_leave(
        employee_id, category, start_date, end_date, reason, substitute_id, is_station_leave
    )
    # Mapping service result to DTO
    return LeaveApplicationSummaryDTO(
        id=result["application_id"],
        employee_id=employee_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=result["status"],
        substitute_id=substitute_id,
    )


def get_my_applications_contract(employee_ids: Sequence[str]) -> list[LeaveApplicationSummaryDTO]:
    """
    Retrieves all leave applications for a sequence of employee IDs.

    NOTE: Accepts a sequence (list/tuple) of employee_id strings to prevent N+1 queries.

    :param employee_ids: Sequence of employee ID strings.
    :return: List of LeaveApplicationSummaryDTO instances.
    """
    # Calls the selector layer and maps results to DTOs
    app_data_list = get_applications_for_employee(employee_ids)
    return [
        LeaveApplicationSummaryDTO(
            id=app["id"],
            employee_id=app["employee_id"],
            category=app["category"],
            start_date=app["start_date"],
            end_date=app["end_date"],
            reason=app["reason"],
            status=app["status"],
            substitute_id=app["substitute_id"],
        )
        for app in app_data_list
    ]


def get_all_applications_contract(approver_ids: Sequence[str]) -> list[LeaveApplicationSummaryDTO]:
    """
    Retrieves all leave applications filtered by approver scope.

    NOTE: Accepts a sequence (list/tuple) of approver ID strings to prevent N+1 queries.
    Pass empty tuple () or ("*",) for "all employees" view.

    :param approver_ids: Sequence of approver employee ID strings (or empty/* for all).
    :return: List of LeaveApplicationSummaryDTO instances.
    """
    # Calls the selector layer and maps results to DTOs
    app_data_list = get_all_applications(approver_ids)
    return [
        LeaveApplicationSummaryDTO(
            id=app["id"],
            employee_id=app["employee_id"],
            category=app["category"],
            start_date=app["start_date"],
            end_date=app["end_date"],
            reason=app["reason"],
            status=app["status"],
            substitute_id=app["substitute_id"],
        )
        for app in app_data_list
    ]


# --- Approval & Status Management Operations ---


def process_leave_approval_contract(
    application_id: int,
    approver_id: str,
    action: str,  # 'approve' or 'reject'
    notes: str | None = None,
) -> dict:
    """
    Approves or rejects a specific leave application.

    :param application_id: The ID of the application to modify.
    :param approver_id: The ID of the user performing the action.
    :param action: 'approve' or 'reject'.
    :param notes: Optional notes on the decision.
    :return: Dictionary confirming the new status and application details.
    """
    # Calls the service layer to perform the mutation
    return approve_application(application_id, approver_id, action, notes)


def update_substitute_response_contract(
    application_id: int,
    substitute_id: str,
    response_status: str,  # 'accepted' or 'declined'
    notes: str | None = None,
) -> SubstituteResponseDTO:
    """
    Allows a substitute employee to accept or decline the coverage request.
    """
    # Calls the service layer to perform the mutation
    result = update_substitute_response(application_id, substitute_id, response_status, notes)
    # Mapping service result to DTO
    return SubstituteResponseDTO(
        application_id=result["application_id"],
        substitute_id=substitute_id,
        response_status=result["new_status"],
        notes=notes,
    )
