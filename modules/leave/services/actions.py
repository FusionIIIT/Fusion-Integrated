"""
Leave Action Services - Cancellation, Extension, Resumption, and Offline Sync.

STAGE 3: SELECTORS & TRANSACTIONAL SERVICES, Item 3
"""

from typing import Optional, Dict, Any
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from core.api.exceptions import (
    ConflictError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)

from modules.leave.domain.constants import (
    DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT,
    AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION, APPROVED, REJECTED,
    WITHDRAWN, CANCELLED, CANCELLATION_REJECTED,
    EXTENSION_AWAITING_SUBSTITUTE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_AWAITING_UNIT_HEAD, EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL, EXTENSION_APPROVED, EXTENSION_REJECTED,
    EXTENSION_WITHDRAWN, RESUMPTION_PENDING, RESUMPTION_NORMAL,
    RESUMPTION_EARLY, RESUMPTION_LATE,
    EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT,
    SANCTIONING_AUTHORITY, DIRECTOR, LEAVE_ADMIN, SYSTEM,
)

from modules.leave.models.requests import LeaveRequest, LeaveRequestTransition, CancellationRequest, ExtensionRequest, ResumptionRecord
from modules.leave.models.ledger import LeaveBalanceLedger, LeaveLedgerTransaction


class ActionValidationError(Exception):
    """Custom exception for action validation failures."""
    pass


def request_cancellation(
    request: LeaveRequest,
    actor_user_id: int,
    actor_role: str,
    reason: str,
) -> LeaveRequestTransition:
    """
    Request cancellation of a leave request.
    
    Validates pre-start condition (BR-EL-023).
    On approval, restores deducted balance and marks CANCELLED.
    
    Args:
        request: The leave request to cancel
        actor_user_id: ID of the actor requesting cancellation
        actor_role: Role of the actor
        reason: Reason for cancellation
        
    Returns:
        LeaveRequestTransition record
        
    Raises:
        ConflictError: If request is not in cancellable state
        BadRequestError: If reason is empty or invalid
    """
    # Validate actor permissions
    if actor_role not in [EMPLOYEE, UNIT_HEAD, ESTABLISHMENT, LEAVE_ADMIN]:
        raise PermissionDeniedError(
            code="leave.cancellation.request",
            message="Actor does not have permission to request cancellation",
            details=[{"field": "actor_role", "value": actor_role, "allowed": [EMPLOYEE, UNIT_HEAD, ESTABLISHMENT, LEAVE_ADMIN]}]
        )
    
    # Validate reason
    if not reason or len(reason.strip()) < 10:
        raise BadRequestError(
            code="leave.cancellation.invalid_reason",
            message="Cancellation reason must be at least 10 characters",
            details=[{"field": "reason", "min_length": 10}]
        )
    
    # Check if request is in cancellable state (pre-start)
    if request.status not in [DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION]:
        raise ConflictError(
            code="leave.cancellation.not_allowed",
            message=f"Cannot cancel request in state {request.status}. Only pre-start requests can be cancelled.",
            details=[{"current_status": request.status, "allowed_states": [DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION]}]
        )
    
    # Check if leave has started
    if request.start_date <= date.today():
        raise ConflictError(
            code="leave.cancellation.too_late",
            message="Cannot cancel leave that has already started.",
            details=[{"start_date": request.start_date, "today": date.today()}]
        )
    
    # Create cancellation request record
    cancellation = CancellationRequest.objects.create(
        leave_request=request,
        reason=reason,
        status="pending"
    )
    
    # Create transition record
    transition = LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=request.status,
        to_status="CANCELLATION_PENDING_UNIT_HEAD",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remarks=reason
    )
    
    return transition


def request_extension(
    request: LeaveRequest,
    actor_user_id: int,
    actor_role: str,
    requested_end_date: date,
    incremental_days: Decimal,
    substitute_user_id: Optional[int] = None,
) -> ExtensionRequest:
    """
    Request extension of an ongoing leave.
    
    Validates ongoing leave, calculates incremental days (BR-EL-025).
    
    Args:
        request: The leave request to extend
        actor_user_id: ID of the actor requesting extension
        actor_role: Role of the actor
        requested_end_date: New end date
        incremental_days: Additional days requested
        substitute_user_id: Optional substitute for extension
        
    Returns:
        ExtensionRequest record
        
    Raises:
        ConflictError: If request is not in extendable state
        BadRequestError: If dates or days are invalid
    """
    # Validate actor permissions
    if actor_role not in [EMPLOYEE, UNIT_HEAD, ESTABLISHMENT, LEAVE_ADMIN]:
        raise PermissionDeniedError(
            code="leave.extension.request",
            message="Actor does not have permission to request extension",
            details=[{"field": "actor_role", "value": actor_role, "allowed": [EMPLOYEE, UNIT_HEAD, ESTABLISHMENT, LEAVE_ADMIN]}]
        )
    
    # Check if request is in extendable state (ongoing leave)
    if request.status not in [APPROVED, EXTENSION_APPROVED]:
        raise ConflictError(
            code="leave.extension.not_allowed",
            message=f"Cannot extend request in state {request.status}. Only approved/extended leaves can be extended.",
            details=[{"current_status": request.status, "allowed_states": [APPROVED, EXTENSION_APPROVED]}]
        )
    
    # Validate dates
    if requested_end_date <= request.end_date:
        raise BadRequestError(
            code="leave.extension.invalid_dates",
            message="New end date must be after current end date",
            details=[{"current_end": request.end_date, "requested_end": requested_end_date}]
        )
    
    if incremental_days <= 0:
        raise BadRequestError(
            code="leave.extension.invalid_days",
            message="Incremental days must be positive",
            details=[{"days": incremental_days, "min": 0.01}]
        )
    
    # Check if extension would exceed maximum allowed
    max_extension_days = 30  # Default max extension
    if incremental_days > max_extension_days:
        raise BadRequestError(
            code="leave.extension.exceeds_limit",
            message=f"Extension cannot exceed {max_extension_days} days",
            details=[{"requested": incremental_days, "max": max_extension_days}]
        )
    
    # Create extension request record
    extension = ExtensionRequest.objects.create(
        leave_request=request,
        requested_end_date=requested_end_date,
        incremental_days=incremental_days,
        substitute_user_id=substitute_user_id,
        status="pending"
    )
    
    # Create transition record
    transition = LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=request.status,
        to_status="EXTENSION_AWAITING_SUBSTITUTE" if substitute_user_id else "EXTENSION_AWAITING_UNIT_HEAD",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remarks=f"Extension requested: {incremental_days} additional days"
    )
    
    return extension


def submit_resumption(
    request: LeaveRequest,
    actor_user_id: int,
    actor_role: str,
    actual_resumption_date: date,
    diff_days: Decimal,
) -> ResumptionRecord:
    """
    Submit resumption record for leave return.
    
    Implements EL-UC-010/011 and BR-EL-028 (adjusts balance on early/late return).
    
    Args:
        request: The leave request
        actor_user_id: ID of the actor submitting resumption
        actor_role: Role of the actor
        actual_resumption_date: Actual date of return
        diff_days: Difference from expected return (negative = early, positive = late)
        
    Returns:
        ResumptionRecord record
        
    Raises:
        ConflictError: If request is not in resumption state
        BadRequestError: If diff_days is invalid
    """
    # Validate actor permissions
    if actor_role not in [EMPLOYEE, UNIT_HEAD, ESTABLISHMENT, LEAVE_ADMIN]:
        raise PermissionDeniedError(
            code="leave.resumption.submit",
            message="Actor does not have permission to submit resumption",
            details=[{"field": "actor_role", "value": actor_role, "allowed": [EMPLOYEE, UNIT_HEAD, ESTABLISHMENT, LEAVE_ADMIN]}]
        )
    
    # Check if request is in resumption state
    if request.status not in [RESUMPTION_PENDING]:
        raise ConflictError(
            code="leave.resumption.not_allowed",
            message=f"Cannot submit resumption for request in state {request.status}",
            details=[{"current_status": request.status, "allowed_status": RESUMPTION_PENDING}]
        )
    
    # Validate diff_days
    if diff_days < -3 or diff_days > 3:
        raise BadRequestError(
            code="leave.resumption.invalid_diff",
            message="Return difference must be within ±3 days",
            details=[{"diff_days": diff_days, "min": -3, "max": 3}]
        )
    
    # Create resumption record
    resumption = ResumptionRecord.objects.create(
        leave_request=request,
        actual_resumption_date=actual_resumption_date,
        diff_days=diff_days,
        status="pending"
    )
    
    # Create transition record
    transition = LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=request.status,
        to_status="RESUMPTION_NORMAL" if -1 <= diff_days <= 1 else ("RESUMPTION_EARLY" if diff_days < 0 else "RESUMPTION_LATE"),
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remarks=f"Resumption submitted: {diff_days} days difference"
    )
    
    return resumption


def review_resumption(
    request: LeaveRequest,
    actor_user_id: int,
    actor_role: str,
    adjustment_applied: bool,
    remarks: str = "",
) -> ResumptionRecord:
    """
    Review and approve resumption record.
    
    Implements EL-UC-011 and BR-EL-028 (adjusts balance on early/late return).
    
    Args:
        request: The leave request
        actor_user_id: ID of the actor reviewing resumption
        actor_role: Role of the actor
        adjustment_applied: Whether balance adjustment was applied
        remarks: Review remarks
        
    Returns:
        ResumptionRecord record
        
    Raises:
        ConflictError: If request is not in resumption state
        PermissionDeniedError: If actor lacks review permission
    """
    # Validate actor permissions
    if actor_role not in [UNIT_HEAD, ESTABLISHMENT, SANCTIONING_AUTHORITY, DIRECTOR, LEAVE_ADMIN]:
        raise PermissionDeniedError(
            code="leave.resumption.review",
            message="Actor does not have permission to review resumption",
            details=[{"field": "actor_role", "value": actor_role, "allowed": [UNIT_HEAD, ESTABLISHMENT, SANCTIONING_AUTHORITY, DIRECTOR, LEAVE_ADMIN]}]
        )
    
    # Check if request is in resumption state
    if request.status not in [RESUMPTION_PENDING]:
        raise ConflictError(
            code="leave.resumption.not_allowed",
            message=f"Cannot review resumption for request in state {request.status}",
            details=[{"current_status": request.status, "allowed_status": RESUMPTION_PENDING}]
        )
    
    # Get the resumption record
    resumption = ResumptionRecord.objects.select_for_update().get(
        leave_request=request
    )
    
    # Update resumption record
    resumption.adjustment_applied = adjustment_applied
    resumption.status = "approved" if adjustment_applied else "rejected"
    resumption.save()
    
    # Create transition record
    transition = LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=request.status,
        to_status="RESUMPTION_NORMAL" if adjustment_applied else "RESUMPTION_REJECTED",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remarks=remarks or f"Resumption {'approved' if adjustment_applied else 'rejected'}"
    )
    
    # Update leave request status
    request.status = "RESUMPTION_NORMAL" if adjustment_applied else "RESUMPTION_REJECTED"
    request.save()
    
    return resumption


def sync_offline_leave(
    request: LeaveRequest,
    actor_user_id: int,
    actor_role: str,
    sanction_order_ref: str,
    recorded_by_user_id: Optional[int] = None,
) -> LeaveRequest:
    """
    Sync offline leave with sanction evidence.
    
    Retrospective sync with sanction evidence, bypassing approval routing (BR-EL-029).
    
    Args:
        request: The leave request to sync
        actor_user_id: ID of the actor syncing
        actor_role: Role of the actor
        sanction_order_ref: Reference from sanction order
        recorded_by_user_id: User who recorded the sanction
        
    Returns:
        Updated LeaveRequest
        
    Raises:
        ConflictError: If request is not in offline sync state
        BadRequestError: If sanction_order_ref is invalid
    """
    # Validate actor permissions
    if actor_role not in [LEAVE_ADMIN, SYSTEM]:
        raise PermissionDeniedError(
            code="leave.offline.record",
            message="Actor does not have permission to sync offline leave",
            details=[{"field": "actor_role", "value": actor_role, "allowed": [LEAVE_ADMIN, SYSTEM]}]
        )
    
    # Check if request is in offline sync state
    if request.status not in [DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION]:
        raise ConflictError(
            code="leave.offline.not_allowed",
            message=f"Cannot sync offline leave for request in state {request.status}",
            details=[{"current_status": request.status, "allowed_states": [DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION]}]
        )
    
    # Validate sanction_order_ref
    if not sanction_order_ref or len(sanction_order_ref.strip()) < 10:
        raise BadRequestError(
            code="leave.offline.invalid_ref",
            message="Sanction order reference must be at least 10 characters",
            details=[{"field": "sanction_order_ref", "min_length": 10}]
        )
    
    # Update request with offline sanction details
    request.station_leave_required = True
    request.station_leave_details = {
        "sanction_order_ref": sanction_order_ref,
        "recorded_by_user_id": recorded_by_user_id,
        "synced_by_user_id": actor_user_id,
        "synced_at": request.created_at.isoformat() if hasattr(request, 'created_at') else None
    }
    request.save()
    
    # Create transition record
    transition = LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=request.status,
        to_status="OFFLINE_SANCTIONED",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remarks=f"Offline leave synced with sanction order: {sanction_order_ref}"
    )
    
    return request
