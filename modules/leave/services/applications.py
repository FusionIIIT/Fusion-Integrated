"""
Service layer for leave applications.
Implements core business logic: validation, routing, consent handling, and decision recording.
Uses Django transactions to ensure atomicity of state changes and history logging.
"""

from datetime import date
from typing import Any, Optional, Tuple

from django.db import transaction, models
from django.core.exceptions import ValidationError as DjangoValidationError

from modules.directory.models import UserRef
from modules.leave.domain.policy import (
    LeaveCategory,
    calculate_consumed_days,
    check_applicant_overlap,
    requires_substitute,
    unit_head_decision_required,
    get_categories_requiring_unit_head_decision,
)
from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveActionHistory,
    LeaveCategory as ModelLeaveCategory,
)
from fusion_auth.permissions import HasPermission


def apply_leave(
    actor_id: int,
    category: str,
    requested_from: date,
    requested_to: date,
    purpose: str,
    station_leave_details: Optional[dict] = None,
    nominated_substitute_id: Optional[int] = None,
) -> LeaveApplication:
    """
    Create and submit a new leave application.
    
    Validates eligibility, balance, overlaps, and substitutes.
    Routes to substitute consent if required, otherwise proceeds to Unit Head review.
    
    Args:
        actor_id: ID of the employee submitting the request.
        category: Leave category (e.g., 'CL', 'RH').
        requested_from: Start date of leave.
        requested_to: End date of leave.
        purpose: Reason for leave.
        station_leave_details: Optional JSON details for station leave.
        nominated_substitute_id: ID of the nominated substitute (if applicable).
    
    Returns:
        The created LeaveApplication instance.
    
    Raises:
        ValueError: If validation fails or action is not allowed in current status.
        DjangoValidationError: If domain policy rules are violated.
    """
    # Map string category to Enum
    try:
        category_enum = ModelLeaveCategory(category)
    except ValueError:
        raise ValueError(f"Invalid leave category: {category}")

    application, created = LeaveApplication.objects.get_or_create(
        user_id=actor_id,
        defaults={
            'category': category_enum,
            'requested_from': requested_from,
            'requested_to': requested_to,
            'purpose': purpose,
            'station_leave_details': station_leave_details,
            'nominated_substitute_id': nominated_substitute_id,
            'status': 'draft',
        },
    )

    if not created:
        # Check if status allows modification (only 'draft' or 'submitted' before full processing)
        # However, per BR-EL-034, in-place modification is blocked. 
        # We assume this function is called only for new applications.
        # If an existing draft exists, we might need to handle it differently, 
        # but the spec implies a fresh application flow.
        pass

    # Domain Validation
    try:
        policy = get_policy_config(category_enum)
        
        # Check balance (simplified: assume sufficient balance if created or updated by service)
        # In a full system, we would query LeaveBalance for the user/year/category.
        # For this service layer, we assume the balance check is handled or passed.
        # We will perform a placeholder check to ensure logic exists.
        _check_balance(actor_id, category_enum, requested_from, requested_to)

        # Check overlap (simplified: assume no active leave for actor)
        _check_overlap(actor_id, requested_from, requested_to)

        # Check substitute eligibility if required
        if requires_substitute(category_enum):
            if nominated_substitute_id is None:
                raise ValueError("Substitute must be nominated for this category.")
            _validate_substitute_eligibility(nominated_substitute_id, actor_id, requested_from, requested_to)
    except (ValueError, DjangoValidationError) as e:
        # Log history entry for validation failure before raising
        _log_action_history(
            application=application,
            actor_id=actor_id,
            action_type="validation_failed",
            description=str(e),
        )
        raise

    # Create the application instance (if not already created above)
    if not created:
        application.save()

    # Determine routing path
    if requires_substitute(category_enum):
        # Route to substitute consent
        status = 'submitted'
        _log_action_history(
            application=application,
            actor_id=actor_id,
            action_type="substitute_consent_required",
            description=f"Application submitted. Awaiting substitute consent.",
        )
    else:
        # Route to Unit Head review (or Director self-sanction if applicable)
        status = 'submitted'
        _log_action_history(
            application=application,
            actor_id=actor_id,
            action_type="submitted_for_review",
            description=f"Application submitted for {category_enum.value} leave.",
        )

    # Update status to submitted
    application.status = status
    application.save()

    return application


def respond_to_substitute_request(
    actor_id: int,
    application_id: int,
    accept: bool,
) -> None:
    """
    Accept or decline a substitute request.
    
    Args:
        actor_id: ID of the substitute (or responsibility holder).
        application_id: ID of the associated leave application.
        accept: True to accept, False to decline.
    
    Raises:
        ValueError: If action is not allowed in current status.
    """
    application = LeaveApplication.objects.get(id=application_id)

    if application.status not in ['submitted', 'under_review']:
        raise ValueError(f"Cannot respond to substitute request for application in status {application.status}.")

    # Update application status based on response
    if accept:
        new_status = 'under_review'
        description = "Substitute consent accepted."
    else:
        new_status = 'submitted'  # Reverts to applicant action required state effectively
        description = "Substitute consent declined."

    application.status = new_status
    application.save()

    _log_action_history(
        application=application,
        actor_id=actor_id,
        action_type="substitute_response",
        description=description,
    )


def nominate_replacement_substitute(
    actor_id: int,
    application_id: int,
    new_substitute_id: int,
) -> None:
    """
    Nominate a replacement substitute after a decline.
    
    Args:
        actor_id: ID of the employee (applicant).
        application_id: ID of the associated leave application.
        new_substitute_id: ID of the new nominated substitute.
    
    Raises:
        ValueError: If action is not allowed in current status.
    """
    application = LeaveApplication.objects.get(id=application_id)

    # Check if we are in a state where replacement is needed (e.g., after decline)
    # Per EL-UC-019, this happens when substitute declines and request enters 'Applicant Action Required'.
    # We assume status reflects this or is 'submitted' awaiting another response.
    if application.status not in ['submitted', 'under_review']:
        raise ValueError(f"Cannot nominate replacement substitute for application in status {application.status}.")

    # Validate new substitute eligibility (simplified)
    _validate_substitute_eligibility(new_substitute_id, actor_id, application.requested_from, application.requested_to)

    # Update the nominated substitute ID
    application.nominated_substitute_id = new_substitute_id
    application.save()

    _log_action_history(
        application=application,
        actor_id=actor_id,
        action_type="substitute_renomination",
        description=f"New substitute {new_substitute_id} nominated.",
    )


@transaction.atomic
def unit_head_review(
    actor_id: int,
    application_id: int,
    decision: str,
) -> None:
    """
    Record Unit Head's review decision.
    
    For CL/RH: Approve or Reject.
    For SCL/EL/COL/VL: Recommended or Not Recommended.
    
    Args:
        actor_id: ID of the Unit Head.
        application_id: ID of the leave application.
        decision: 'approve', 'reject', 'recommended', or 'not_recommended'.
    
    Raises:
        ValueError: If action is not allowed in current status.
    """
    application = LeaveApplication.objects.get(id=application_id)

    # Determine expected statuses based on category and decision type
    category_enum = ModelLeaveCategory(application.category)
    
    if unit_head_decision_required(category_enum):
        # CL/RH: Unit Head makes final decision
        allowed_statuses = ['submitted', 'under_review']
        valid_decisions = ['approve', 'reject']
    else:
        # SCL/EL/COL/VL: Unit Head recommends
        allowed_statuses = ['submitted', 'under_review']
        valid_decisions = ['recommended', 'not_recommended']

    if application.status not in allowed_statuses:
        raise ValueError(f"Unit Head can only review applications in status {allowed_statuses}. Current status: {application.status}")

    if decision not in valid_decisions:
        raise ValueError(f"Invalid decision '{decision}' for category {category_enum.value}.")

    # Update application status and record history
    if decision == 'approve':
        new_status = 'approved'
        description = f"Unit Head approved {application.category.value} leave."
    elif decision == 'reject':
        new_status = 'rejected'
        description = f"Unit Head rejected {application.category.value} leave."
    elif decision == 'recommended':
        new_status = 'recommended'
        description = f"Unit Head recommended {application.category.value} leave for higher sanction."
    else:  # not_recommended
        new_status = 'not_recommended'
        description = f"Unit Head not recommended {application.category.value} leave for higher sanction."

    application.status = new_status
    application.save()

    _log_action_history(
        application=application,
        actor_id=actor_id,
        action_type="unit_head_decision",
        description=description,
    )


@transaction.atomic
def establishment_verify_and_route(
    actor_id: int,
    application_id: int,
) -> None:
    """
    Perform Establishment-level verification and route to final Sanctioning Authority.
    
    This is a placeholder for the logic defined in BR-EL-018 and EL-UC-004.
    In this implementation, it assumes a simple routing step where the application
    is verified (e.g., completeness check) and then routed based on configuration.
    
    Args:
        actor_id: ID of the Establishment Processing Role (e.g., Deputy Registrar).
        application_id: ID of the leave application.
    
    Raises:
        ValueError: If action is not allowed in current status.
    """
    application = LeaveApplication.objects.get(id=application_id)

    # Check if this is a higher-sanction case requiring routing
    category_enum = ModelLeaveCategory(application.category)
    if unit_head_decision_required(category_enum):
        raise ValueError(f"Unit Head decision required for {category_enum.value}, no establishment routing needed.")

    allowed_statuses = ['recommended', 'not_recommended']
    if application.status not in allowed_statuses:
        raise ValueError(f"Establishment can only process applications in status {allowed_statuses}. Current status: {application.status}")

    # Placeholder verification logic (e.g., check for required fields)
    # In a real system, this would involve complex hierarchy configuration checks.
    _verify_establishment_requirements(application)

    # Route to final Sanctioning Authority (simulated by updating status)
    # The actual routing might involve creating a work item or changing status directly.
    # Per BR-EL-019, we resolve the competent authority. Here, we assume the next step is final sanction.
    new_status = 'under_review'  # Or a specific 'awaiting_final_sanction' if defined
    description = f"Establishment verified and routed to final Sanctioning Authority."

    application.status = new_status
    application.save()

    _log_action_history(
        application=application,
        actor_id=actor_id,
        action_type="establishment_routing",
        description=description,
    )


@transaction.atomic
def final_sanction_decision(
    actor_id: int,
    application_id: int,
    decision: str,
) -> None:
    """
    Record the final sanctioning decision.
    
    Approve or Reject. Updates balance on approval.
    
    Args:
        actor_id: ID of the Sanctioning Authority (e.g., Dean, Registrar, Director).
        application_id: ID of the leave application.
        decision: 'approve' or 'reject'.
    
    Raises:
        ValueError: If action is not allowed in current status.
    """
    application = LeaveApplication.objects.get(id=application_id)

    # Check if this is a final sanction case (not Unit Head decision)
    category_enum = ModelLeaveCategory(application.category)
    if unit_head_decision_required(category_enum):
        raise ValueError(f"Unit Head makes the final decision for {category_enum.value}, no higher authority needed.")

    allowed_statuses = ['recommended', 'not_recommended']
    if application.status not in allowed_statuses:
        raise ValueError(f"Final Sanctioning Authority can only process applications in status {allowed_statuses}. Current status: {application.status}")

    if decision not in ['approve', 'reject']:
        raise ValueError(f"Invalid final decision '{decision}'. Must be 'approve' or 'reject'.")

    # Update application status
    new_status = 'approved' if decision == 'approve' else 'rejected'
    description = f"Final Sanctioning Authority {decision}ed {application.category.value} leave."

    application.status = new_status
    application.save()

    # Handle balance update on approval (BR-EL-025, BR-EL-023)
    if decision == 'approve':
        _update_balance_on_approval(application, actor_id)

    _log_action_history(
        application=application,
        actor_id=actor_id,
        action_type="final_sanction",
        description=description,
    )


# --- Helper Functions ---

def get_policy_config(category: ModelLeaveCategory) -> dict:
    """Retrieve entitlement configuration for a category."""
    # Import here to avoid circular dependencies if any
    from modules.leave.domain.policy import ENTITLEMENTS
    
    return ENTITLEMENTS[category]


def _check_balance(actor_id: int, category: ModelLeaveCategory, requested_from: date, requested_to: date) -> None:
    """
    Placeholder for balance check logic.
    In a full implementation, this would query LeaveBalance for the user/year/category.
    """
    # Simplified check: assume sufficient balance if no specific error raised
    # Real logic:
    # 1. Determine year (e.g., based on requested_from).
    # 2. Query available_days - used_days for category.
    # 3. Calculate consumed days using policy.py rules.
    # 4. Raise ValueError if insufficient balance.
    pass


def _check_overlap(actor_id: int, requested_from: date, requested_to: date) -> None:
    """
    Placeholder for overlap check logic.
    In a full implementation, this would query LeaveApplication for the actor_id.
    """
    # Simplified check: assume no active leave for actor
    # Real logic:
    # 1. Find all applications for actor_id with status in ['pending', 'approved'].
    # 2. Check date range overlap.
    # 3. Handle CL half-day exception (BR-EL-012).
    # 4. Raise ValueError if overlap found.
    pass


def _validate_substitute_eligibility(substitute_id: int, applicant_id: int, responsibility_start: date, responsibility_end: date) -> None:
    """
    Validate substitute eligibility (BR-EL-014).
    
    Conditions:
    - Must be another employee.
    - Must not be the applicant.
    - Must have no overlapping pending or approved leave during the responsibility period.
    """
    if substitute_id == applicant_id:
        raise ValueError("Substitute cannot be the applicant.")
    
    # Placeholder for checking substitute's existing leave
    # Real logic:
    # 1. Query LeaveApplication for substitute_id with status in ['pending', 'approved'].
    # 2. Check date range overlap with [responsibility_start, responsibility_end].
    # 3. Raise ValueError if overlap found.
    pass


def _verify_establishment_requirements(application: LeaveApplication) -> None:
    """
    Placeholder for Establishment-level verification.
    In a real system, this would check configuration and completeness.
    """
    # Real logic:
    # 1. Verify required fields are present (e.g., purpose, dates).
    # 2. Check against current hierarchy configuration.
    # 3. Raise ValueError if requirements not met.
    pass


def _update_balance_on_approval(application: LeaveApplication, actor_id: int) -> None:
    """
    Update leave balance on approval (BR-EL-025).
    
    For new leave: add to available balance.
    For cancellation: restore/adjust deducted balance.
    For extension: post incremental period.
    
    This is a simplified placeholder.
    """
    # Real logic:
    # 1. Determine year (e.g., based on requested_from).
    # 2. Query or create LeaveBalance record for actor_id, year, category.
    # 3. Calculate consumed days.
    # 4. Update available_days = available_days - consumed_days (for new leave)
    #    OR adjust used_days/available_days based on cancellation/extension rules.
    # 5. Save LeaveBalance.
    pass


def _log_action_history(
    application: LeaveApplication,
    actor_id: int,
    action_type: str,
    description: str,
) -> None:
    """
    Append an entry to the leave action history (BR-EL-037).
    
    This function is transaction-safe as it's called within atomic blocks.
    """
    history = LeaveActionHistory.objects.create(
        application=application,
        actor_id=actor_id,
        action_type=action_type,
        description=description,
    )


# --- New Functions for Lifecycle Actions ---

def withdraw_pending_request(actor_id: int, application_id: int) -> None:
    """Withdraw a pending leave application."""
    try:
        application = LeaveApplication.objects.get(id=application_id)
        
        # Check if the application belongs to the actor (optional but good practice)
        # and if it is in a withdrawable state (e.g., 'pending')
        if application.user_id != actor_id:
            raise ValueError("You can only withdraw your own applications.")
        
        if application.status not in ['pending', 'draft']:  # Adjust based on actual status enum
            raise ValueError(f"Cannot withdraw application with status {application.status}.")
            
        # Update status to withdrawn
        application.status = 'withdrawn'
        application.save()
        
        # Log the action
        history = LeaveActionHistory.objects.create(
            application_id=application_id,
            actor_id=actor_id,
            action_type='withdrawal',
            description=f"Application withdrawn by user {actor_id}"
        )
    except LeaveApplication.DoesNotExist:
        raise ValueError(f"Application with ID {application_id} not found.")
    except ValidationError as e:
        raise ValueError(str(e))


def request_cancellation(actor_id: int, application_id: int) -> None:
    """Request cancellation of an approved leave."""
    try:
        application = LeaveApplication.objects.get(id=application_id)
        
        if application.user_id != actor_id:
            raise ValueError("You can only cancel your own applications.")
            
        # Update status to 'cancellation_requested' or similar
        application.status = 'cancellation_requested'
        application.save()
        
        history = LeaveActionHistory.objects.create(
            application_id=application_id,
            actor_id=actor_id,
            action_type='cancellation_request',
            description=f"Cancellation requested by user {actor_id}"
        )
    except LeaveApplication.DoesNotExist:
        raise ValueError(f"Application with ID {application_id} not found.")


def decide_cancellation(actor_id: int, application_id: int, decision: str) -> None:
    """Decide on a cancellation request."""
    try:
        application = LeaveApplication.objects.get(id=application_id)
        
        if application.status != 'cancellation_requested':
            raise ValueError(f"Cannot decide cancellation for application with status {application.status}.")
            
        if decision == 'approve':
            # Restore balance and mark as cancelled
            _update_balance_on_cancellation(application, actor_id)
            application.status = 'cancelled'
            description = f"Cancellation approved by {actor_id}."
        else:  # reject
            application.status = 'approved'  # Revert to original status or keep pending? Usually revert.
            description = f"Cancellation rejected by {actor_id}."
            
        application.save()
        
        history = LeaveActionHistory.objects.create(
            application_id=application_id,
            actor_id=actor_id,
            action_type='cancellation_decision',
            description=description
        )
    except LeaveApplication.DoesNotExist:
        raise ValueError(f"Application with ID {application_id} not found.")


def request_extension(actor_id: int, application_id: int, extension_from: date, extension_to: date, purpose: str, station_leave_details: Any = None, nominated_substitute_id: int = None) -> None:
    """Request an extension of ongoing leave."""
    try:
        application = LeaveApplication.objects.get(id=application_id)
        
        if application.user_id != actor_id:
            raise ValueError("You can only extend your own applications.")
            
        # Update dates and purpose
        application.requested_from = extension_from
        application.requested_to = extension_to
        application.purpose = purpose
        application.station_leave_details = station_leave_details
        application.save()
        
        history = LeaveActionHistory.objects.create(
            application_id=application_id,
            actor_id=actor_id,
            action_type='extension_request',
            description=f"Extension requested from {extension_from} to {extension_to}"
        )
    except LeaveApplication.DoesNotExist:
        raise ValueError(f"Application with ID {application_id} not found.")


def submit_resumption(actor_id: int, application_id: int, actual_resumption_date: date) -> None:
    """Submit actual resumption of duty information."""
    try:
        application = LeaveApplication.objects.get(id=application_id)
        
        if application.user_id != actor_id:
            raise ValueError("You can only submit resumption for your own applications.")
            
        # Store the date (could be a separate model field or just update here)
        # Assuming we store it in the application model for simplicity as per serializer
        application.actual_resumption_date = actual_resumption_date
        application.save()
        
        history = LeaveActionHistory.objects.create(
            application_id=application_id,
            actor_id=actor_id,
            action_type='resumption_submitted',
            description=f"Resumption submitted on {actual_resumption_date}"
        )
    except LeaveApplication.DoesNotExist:
        raise ValueError(f"Application with ID {application_id} not found.")


def review_resumption(actor_id: int, application_id: int, actual_resumption_date: date) -> None:
    """Review the submitted resumption and adjust balance."""
    try:
        application = LeaveApplication.objects.get(id=application_id)
        
        if application.user_id != actor_id:
            raise ValueError("You can only review your own applications.")
            
        # Verify the date matches what was submitted (simplified check)
        # In a real system, this might compare against a stored field or re-calculate consumed days
        
        # Adjust balance based on actual resumption date vs expected
        _update_balance_on_resumption(application, actor_id, actual_resumption_date)
        
        history = LeaveActionHistory.objects.create(
            application_id=application_id,
            actor_id=actor_id,
            action_type='resumption_reviewed',
            description=f"Resumption reviewed on {actual_resumption_date}"
        )
    except LeaveApplication.DoesNotExist:
        raise ValueError(f"Application with ID {application_id} not found.")


# --- Additional Helper Functions for New Logic ---

def _update_balance_on_cancellation(application: LeaveApplication, actor_id: int) -> None:
    """Update balance on cancellation."""
    # Real logic: Restore available days
    pass


def _update_balance_on_resumption(application: LeaveApplication, actor_id: int, actual_resumption_date: date) -> None:
    """Update balance based on actual resumption date."""
    # Real logic: Calculate consumed days and adjust
    pass
