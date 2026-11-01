"""Service functions for multi-tier IWD estimate reviews and supervisory decisions.

Implements:
- UC-IWD-031: Review Low-Cost Estimate (BW-IWD-02 Step 2 / BR-IWD-004)
- UC-IWD-041: Conduct Mid-Range Review (BW-IWD-03 Steps 2-3, BW-IWD-04 Step 1 / BR-IWD-005, BR-IWD-006)
- UC-IWD-051: Director Review and Approval (BW-IWD-04 Step 2, BW-IWD-05 Step 2 / BR-IWD-006, BR-IWD-007)
- BR-IWD-001: Active-role authorization isolation
- BR-IWD-009: Mandatory rejection reason retention (AFR-IWD-024)
- BR-IWD-013: Audit logging of approval and rejection decisions (CFR-IWD-11)
"""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.iwd.domain.state_machine import IWDState, transition_estimate_approval
from modules.iwd.models import Complaint, ComplaintTransition


def review_low_cost_estimate(
    *,
    complaint_id: int,
    principal,
    action: str,
    remarks: str = "",
) -> Complaint:
    """IWD Admin approves or rejects an estimate below ₹25,000 (BW-IWD-02 Step 2 / UC-IWD-031)."""
    if principal is None or getattr(principal, "active_role", None) != "iwd_admin":
        raise PermissionDeniedError(
            "An active role of 'iwd_admin' is required to review low-cost estimates.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.estimate.review_low"):
        raise PermissionDeniedError(
            "Permission 'iwd.estimate.review_low' is required.",
            code="permission_denied",
        )

    if action not in ("approve", "reject"):
        raise BadRequestError(
            f"Invalid action '{action}' for low-cost review. Must be 'approve' or 'reject'.",
            code="invalid_review_action",
        )

    cleaned_remarks = remarks.strip() if remarks else ""
    if action == "reject" and not cleaned_remarks:
        raise BadRequestError(
            "A non-blank rejection reason is required (AFR-IWD-024, BR-IWD-009).",
            code="missing_rejection_reason",
        )

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status != IWDState.LOW_COST_REVIEW_PENDING.value:
            raise ConflictError(
                f"Cannot perform low-cost review on complaint in status '{complaint.status}'. "
                f"Complaint must be in '{IWDState.LOW_COST_REVIEW_PENDING.value}'.",
                code="invalid_state_transition",
            )

        new_state = transition_estimate_approval(
            current_state=IWDState(complaint.status),
            action=action,
            actor_role="IWD Admin",
        )

        from_status = complaint.status
        complaint.status = new_state.value
        complaint.save(update_fields=["status", "updated_at"])

        reason = cleaned_remarks if cleaned_remarks else (
            "Low-cost estimate approved" if action == "approve" else "Low-cost estimate rejected"
        )

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=new_state.value,
            actor_user_id=principal.user_id,
            actor_label="IWD Admin",
            reason=reason,
        )

    return complaint


def record_committee_review(
    *,
    complaint_id: int,
    principal,
    remarks: str,
) -> Complaint:
    """Review Committee records necessity/feasibility review for mid-range estimate (BW-IWD-03 Step 2 / UC-IWD-041)."""
    if principal is None or getattr(principal, "active_role", None) != "Department Head":
        raise PermissionDeniedError(
            "An active role of 'Department Head' is required to record committee review.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.estimate.review_committee"):
        raise PermissionDeniedError(
            "Permission 'iwd.estimate.review_committee' is required.",
            code="permission_denied",
        )

    cleaned_remarks = remarks.strip() if remarks else ""
    if not cleaned_remarks:
        raise BadRequestError(
            "Committee necessity/feasibility findings are required (BR-IWD-005, AFR-IWD-019).",
            code="missing_committee_findings",
        )

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status != IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value:
            raise ConflictError(
                f"Cannot record committee review on complaint in status '{complaint.status}'. "
                f"Complaint must be in '{IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value}'.",
                code="invalid_state_transition",
            )

        new_state = transition_estimate_approval(
            current_state=IWDState(complaint.status),
            action="record_committee_review",
            actor_role="Review Committee",
        )

        from_status = complaint.status
        complaint.status = new_state.value
        complaint.save(update_fields=["status", "updated_at"])

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=new_state.value,
            actor_user_id=principal.user_id,
            actor_label="Review Committee",
            reason=f"Committee review: {cleaned_remarks}",
        )

    return complaint


def review_dept_head_estimate(
    *,
    complaint_id: int,
    principal,
    action: str,
    remarks: str = "",
) -> Complaint:
    """Department Head approves, rejects, or forwards a mid-range estimate (BW-IWD-03 Step 3, BW-IWD-04 Step 1 / UC-IWD-041)."""
    if principal is None or getattr(principal, "active_role", None) != "Department Head":
        raise PermissionDeniedError(
            "An active role of 'Department Head' is required for Department Head supervisory review.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.estimate.review_mid"):
        raise PermissionDeniedError(
            "Permission 'iwd.estimate.review_mid' is required.",
            code="permission_denied",
        )

    if action not in ("approve", "reject", "forward_to_director"):
        raise BadRequestError(
            f"Invalid action '{action}' for Department Head review. Must be 'approve', 'reject', or 'forward_to_director'.",
            code="invalid_review_action",
        )

    cleaned_remarks = remarks.strip() if remarks else ""
    if action == "reject" and not cleaned_remarks:
        raise BadRequestError(
            "A non-blank rejection reason is required (AFR-IWD-024, BR-IWD-009).",
            code="missing_rejection_reason",
        )

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status != IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value:
            raise ConflictError(
                f"Cannot perform Department Head supervisory review on complaint in status '{complaint.status}'. "
                f"Complaint must be in '{IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value}'.",
                code="invalid_state_transition",
            )

        new_state = transition_estimate_approval(
            current_state=IWDState(complaint.status),
            action=action,
            actor_role="Department Head",
        )

        from_status = complaint.status
        complaint.status = new_state.value
        complaint.save(update_fields=["status", "updated_at"])

        if action == "reject":
            reason = cleaned_remarks
        elif action == "forward_to_director":
            reason = cleaned_remarks if cleaned_remarks else "Forwarded to Director"
        else:
            reason = cleaned_remarks if cleaned_remarks else "Mid-range estimate approved"

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=new_state.value,
            actor_user_id=principal.user_id,
            actor_label="Department Head",
            reason=reason,
        )

    return complaint


def review_director_estimate(
    *,
    complaint_id: int,
    principal,
    action: str,
    remarks: str = "",
) -> Complaint:
    """Director reviews forwarded mid-range or high-cost estimate (BW-IWD-04 Step 2, BW-IWD-05 Step 2 / UC-IWD-051)."""
    if principal is None or getattr(principal, "active_role", None) != "Director":
        raise PermissionDeniedError(
            "An active role of 'Director' is required for Director review.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.estimate.review_director"):
        raise PermissionDeniedError(
            "Permission 'iwd.estimate.review_director' is required.",
            code="permission_denied",
        )

    cleaned_remarks = remarks.strip() if remarks else ""

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        allowed_states = (
            IWDState.DIRECTOR_REVIEW_PENDING_MID.value,
            IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value,
        )
        if complaint.status not in allowed_states:
            raise ConflictError(
                f"Cannot perform Director review on complaint in status '{complaint.status}'. "
                f"Complaint must be in one of {allowed_states}.",
                code="invalid_state_transition",
            )

        is_high_cost = complaint.status == IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value

        if is_high_cost:
            valid_actions = ("approve", "approve_bidding", "reject", "reject_bidding")
        else:
            valid_actions = ("approve", "reject")

        if action not in valid_actions:
            raise BadRequestError(
                f"Invalid action '{action}' for Director review in status '{complaint.status}'. "
                f"Must be one of {valid_actions}.",
                code="invalid_review_action",
            )

        if action in ("reject", "reject_bidding") and not cleaned_remarks:
            raise BadRequestError(
                "A non-blank rejection reason is required (AFR-IWD-024, BR-IWD-009).",
                code="missing_rejection_reason",
            )

        new_state = transition_estimate_approval(
            current_state=IWDState(complaint.status),
            action=action,
            actor_role="Director",
        )

        from_status = complaint.status
        complaint.status = new_state.value
        complaint.save(update_fields=["status", "updated_at"])

        if action in ("reject", "reject_bidding"):
            reason = cleaned_remarks
        elif is_high_cost:
            reason = cleaned_remarks if cleaned_remarks else "High-cost bidding authorized"
        else:
            reason = cleaned_remarks if cleaned_remarks else "Forwarded mid-range estimate approved"

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=new_state.value,
            actor_user_id=principal.user_id,
            actor_label="Director",
            reason=reason,
        )

    return complaint


def execute_estimate_review(
    *,
    complaint_id: int,
    principal,
    action: str,
    remarks: str = "",
) -> Complaint:
    """Dispatcher entrypoint that inspects complaint status and routes to appropriate review service."""
    try:
        complaint = Complaint.objects.get(pk=complaint_id)
    except Complaint.DoesNotExist:
        raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

    st = complaint.status
    if st == IWDState.LOW_COST_REVIEW_PENDING.value:
        return review_low_cost_estimate(complaint_id=complaint_id, principal=principal, action=action, remarks=remarks)
    elif st == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value:
        return record_committee_review(complaint_id=complaint_id, principal=principal, remarks=remarks)
    elif st == IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value:
        return review_dept_head_estimate(complaint_id=complaint_id, principal=principal, action=action, remarks=remarks)
    elif st in (IWDState.DIRECTOR_REVIEW_PENDING_MID.value, IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value):
        return review_director_estimate(complaint_id=complaint_id, principal=principal, action=action, remarks=remarks)
    else:
        raise ConflictError(
            f"Complaint #{complaint_id} is in status '{st}', which is not an active estimate review state.",
            code="not_in_review_state",
        )

