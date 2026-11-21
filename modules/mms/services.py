from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import (
    RoleAssignment, MessRole,
    RegistrationWindow, RegistrationRequest, RegistrationStatus,
    DeregistrationRequest, DeregistrationStatus,
    RebateRequest, RebateReason, RebateStatus,
    SpecialFoodRequest, SpecialFoodStatus
)

# --- Role Assignment Services (BR-MMS-003, BR-MMS-004, BR-MMS-006, BR-MMS-007) ---
@transaction.atomic
def assign_operational_role(user, role_type: MessRole, duration_days: int = None):
    # Enforce exactly one active role rule by deactivating existing
    now = timezone.now()
    RoleAssignment.objects.filter(role=role_type, is_active=True).update(
        is_active=False,
        end_time=now
    )
    end = now + timedelta(days=duration_days) if duration_days else None
    return RoleAssignment.objects.create(
        user=user,
        role=role_type,
        start_time=now,
        end_time=end,
        is_active=True
    )

# --- Registration Workflows (CW-MMS-01, BR-MMS-009, BR-MMS-010) ---
@transaction.atomic
def submit_registration(student, window_id: int):
    window = RegistrationWindow.objects.get(id=window_id)
    if not window.is_currently_active():
        raise ValidationError("Registration window is closed.")
    if RegistrationRequest.objects.filter(student=student, window=window, status=RegistrationStatus.PENDING).exists():
        raise ValidationError("Registration already pending.")
    return RegistrationRequest.objects.create(student=student, window=window)

@transaction.atomic
def review_registration(request_id: int, decision: str, remarks: str = ""):
    req = RegistrationRequest.objects.select_for_update().get(id=request_id)
    if req.status != RegistrationStatus.PENDING:
        raise ValidationError("Request has already been decided.")
    req.status = RegistrationStatus.APPROVED if decision == 'approve' else RegistrationStatus.REJECTED
    req.remarks = remarks
    req.decided_at = timezone.now()
    req.save()
    return req

# --- Deregistration Workflows (CW-MMS-02, BR-MMS-013, MMS-UC-027) ---
@transaction.atomic
def submit_deregistration(student):
    if DeregistrationRequest.objects.filter(student=student, status=DeregistrationStatus.PENDING).exists():
        raise ValidationError("Deregistration already pending.")
    return DeregistrationRequest.objects.create(student=student)

@transaction.atomic
def review_deregistration(request_id: int, decision: str, remarks: str = ""):
    req = DeregistrationRequest.objects.select_for_update().get(id=request_id)
    if req.status != DeregistrationStatus.PENDING:
        raise ValidationError("Request already decided.")
    
    today = timezone.now().date()
    req.decision_date = today
    req.remarks = remarks
    if decision == 'approve':
        req.status = DeregistrationStatus.APPROVED_AWAITING_EFFECTIVE
        req.effective_date = today + timedelta(days=1)
    else:
        req.status = DeregistrationStatus.REJECTED
    req.save()
    return req

def activate_due_deregistrations():
    """Event-triggered task for MMS-UC-027 (Scheduled at 00:00)."""
    today = timezone.now().date()
    DeregistrationRequest.objects.filter(
        status=DeregistrationStatus.APPROVED_AWAITING_EFFECTIVE,
        effective_date__lte=today
    ).update(status=DeregistrationStatus.EFFECTIVE)

# --- Rebate Workflows (CW-MMS-03, BR-MMS-021..025) ---
@transaction.atomic
def submit_rebate(student, reason: str, explanation: str, start_date, end_date):
    today = timezone.now().date()
    if start_date <= today:
        raise ValidationError("Rebate must be submitted at least 1 calendar day before start date.")
    if (end_date - start_date).days + 1 < 3:
        raise ValidationError("Minimum rebate duration is 3 days.")
    if reason == RebateReason.OTHER and not explanation.strip():
        raise ValidationError("Explanation required when reason is Other.")
    
    # Overlap check
    overlap = RebateRequest.objects.filter(
        student=student,
        status__in=[RebateStatus.PENDING, RebateStatus.APPROVED],
        start_date__lte=end_date,
        end_date__gte=start_date
    ).exists()
    if overlap:
        raise ValidationError("Overlapping rebate request exists.")
    
    return RebateRequest.objects.create(
        student=student, reason=reason, explanation=explanation,
        start_date=start_date, end_date=end_date
    )

@transaction.atomic
def review_rebate(request_id: int, decision: str, approved_start=None, approved_end=None):
    req = RebateRequest.objects.select_for_update().get(id=request_id)
    if req.status != RebateStatus.PENDING:
        raise ValidationError("Rebate already decided.")
    if decision == 'approve':
        req.status = RebateStatus.APPROVED
        req.approved_start_date = approved_start or req.start_date
        req.approved_end_date = approved_end or req.end_date
    else:
        req.status = RebateStatus.REJECTED
    req.save()
    return req

# --- Special Food Workflows (CW-MMS-05, BR-MMS-028..031, MMS-UC-029) ---
@transaction.atomic
def submit_special_food(student, reason: str, requested_date, charge=0.0):
    today = timezone.now().date()
    if requested_date <= today:
        raise ValidationError("Special food must be requested at least 1 calendar day in advance.")
    
    # Institution defined window: default 12 hours from now
    timeout = timezone.now() + timedelta(hours=12)
    return SpecialFoodRequest.objects.create(
        student=student, reason=reason, requested_date=requested_date,
        charge=charge, timeout_at=timeout
    )

@transaction.atomic
def review_special_food(request_id: int, decision: str):
    req = SpecialFoodRequest.objects.select_for_update().get(id=request_id)
    if req.status != SpecialFoodStatus.REQUESTED:
        raise ValidationError("Request is no longer pending.")
    req.status = SpecialFoodStatus.APPROVED if decision == 'approve' else SpecialFoodStatus.REJECTED
    req.save()
    return req

@transaction.atomic
def update_special_food_fulfillment(request_id: int, outcome: str):
    req = SpecialFoodRequest.objects.select_for_update().get(id=request_id)
    if req.status != SpecialFoodStatus.APPROVED:
        raise ValidationError("Can only transition to Served/Cancelled from Approved state.")
    if outcome not in [SpecialFoodStatus.SERVED, SpecialFoodStatus.CANCELLED]:
        raise ValidationError("Outcome must be 'served' or 'cancelled'.")
    req.status = outcome
    req.save()
    return req

def auto_reject_timed_out_special_food():
    """Event-triggered task for MMS-UC-029."""
    SpecialFoodRequest.objects.filter(
        status=SpecialFoodStatus.REQUESTED,
        timeout_at__lte=timezone.now()
    ).update(status=SpecialFoodStatus.REJECTED)