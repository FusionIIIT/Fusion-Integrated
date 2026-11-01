"""
Business Logic Layer (Services) for Employee Leave Management (ELM).

This module contains all transaction and mutation services, implementing the core
business rules by utilizing the domain logic (LeaveCalculator) and persistent storage (models.py).
"""

import datetime

from modules.leave_elm.domain.leave_calculator import LeaveCalculator
from modules.leave_elm.models import LeaveApplication, LeaveBalance, SubstituteResponse


def apply_leave(
    employee_id: str,
    category: str,
    start_date_str: str,
    end_date_str: str,
    reason: str,
    substitute_id: str | None,
    is_station_leave: bool,
    is_half_day_start: bool = False,
    is_half_day_end: bool = False,
) -> dict:
    """
    Creates a new leave application and checks/updates the available balance.

    NOTE: We assume date strings are valid 'YYYY-MM-DD' format.

    :return: Dictionary containing the new application ID and status.
    :raises ValueError: If balance check fails or dates are invalid.
    """

    # 1. Date conversion
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.") from e

    # 2. Calculate duration using domain logic
    if category == "CL":
        duration = LeaveCalculator.calculate_cl_days(
            start_date, end_date, is_half_day_start, is_half_day_end
        )
    elif category in ["RH", "SCL"]:
        duration = LeaveCalculator.calculate_working_days(start_date, end_date)
    elif category in ["EL", "VL", "COL"]:
        duration = LeaveCalculator.calculate_continuous_days(start_date, end_date)
    else:
        raise ValueError(f"Unknown leave category: {category}")

    # 3. Check Balance
    try:
        balance = LeaveBalance.objects.get(user_id=employee_id, category=category)
    except LeaveBalance.DoesNotExist:
        # Initialize balance if missing
        balance = LeaveBalance(
            user_id=employee_id, category=category, available_balance=0.0, annual_entitlement=0.0
        )
        balance.save()

    if balance.available_balance < duration:
        msg = (
            f"Insufficient balance. Required: {duration} days, "
            f"Available: {balance.available_balance} days."
        )
        raise ValueError(msg)

    # 4. Create Application (MUTATE phase)
    application = LeaveApplication.objects.create(
        employee_id=employee_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        substitute_id=substitute_id,
        is_station_leave=is_station_leave,
        duration_days=duration,
        status="pending",
        is_half_day_start=is_half_day_start,
        is_half_day_end=is_half_day_end,
    )

    # 5. Decrement Balance (MUTATE phase)
    balance.available_balance -= duration
    balance.save()

    # 6. Create Substitute Response placeholder if nominated
    if substitute_id:
        SubstituteResponse.objects.create(
            application=application,
            substitute_id=substitute_id,
            response_status="pending",
        )

    return {"application_id": application.pk, "status": application.status}


def reject_application(application_id: int, approver_id: str, notes: str | None = None) -> dict:
    """
        Rejects a leave application.

        :param application_id: The PK of the application.
        :param approver_id: The ID of the user performing the action.
    if application.status in ["rejected", "cancelled"]:
            raise ValueError("Application is already closed.")

    application.status = "rejected"
    application.save()

    return {
        "application_id": application.pk,
        "new_status": application.status,
        "rejected_by": approver_id,
        "notes": notes,
    }
        :param notes: Optional notes.
        :return: Dictionary confirming the new status and application details.
    """
    try:
        application = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist as e:
        raise ValueError("Application not found.") from e

    if application.status in ["rejected", "cancelled"]:
        raise ValueError("Application is already closed.")

    application.status = "rejected"
    application.save()

    return {
        "application_id": application.pk,
        "new_status": application.status,
        "rejected_by": approver_id,
        "notes": notes,
    }


def approve_application(
    application_id: int, approver_id: str, action: str, notes: str | None = None
) -> dict:
    """
    Approves or rejects a leave application and updates the balance accordingly.

    :param application_id: The PK of the application.
    :param approver_id: The ID of the user performing the action.
    :param action: 'approve' or 'reject'.
    :param notes: Optional notes.
    :return: Dictionary confirming the new status and application details.
    """
    try:
        application = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist as e:
        raise ValueError("Application not found.") from e

    if application.status not in ["pending"]:
        raise ValueError(
            f"Application is already in status: {application.status}. Cannot {action}."
        )

    # Status Update
    if action == "approve":
        # Initial approval/recommendation step
        application.status = "recommended"
        application.approved_by_id = approver_id
    elif action == "reject":
        application.status = "rejected"
    else:
        raise ValueError("Invalid action. Must be 'approve' or 'reject'.")

    application.save()
    return {
        "application_id": application.pk,
        "new_status": application.status,
        "approved_by": approver_id,
    }


def update_substitute_response(
    application_id: int, substitute_id: str, response_status: str, notes: str | None = None
) -> dict:
    """
    Updates the status of a substitute's consent.

    :param application_id: The PK of the leave application.
    :param substitute_id: The ID of the substitute responding.
    :param response_status: 'accepted' or 'declined'.
    :param notes: Optional notes.
    :return: Dictionary confirming the updated substitute status.
    """
    try:
        # Ensure application exists before modifying substitute response
        LeaveApplication.objects.get(pk=application_id)

        response, _created = SubstituteResponse.objects.get_or_create(
            application_id=application_id,
            substitute_id=substitute_id,
            defaults={"response_status": response_status, "notes": notes},
        )
        response.response_status = response_status
        response.notes = notes
        response.save()
    except (LeaveApplication.DoesNotExist, ValueError) as e:
        raise ValueError(f"Error updating substitute response: {e!s}") from e
    else:
        return {
            "application_id": application_id,
            "substitute_id": substitute_id,
            "new_status": response_status,
            "message": "Substitute response updated successfully.",
        }
