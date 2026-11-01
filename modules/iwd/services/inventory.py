"""Service functions for IWD inventory verification, stock shortage procurement, and material issuance.

Implements:
- UC-IWD-061: Check Stock and Issue Material (BW-IWD-06 Step 1, BW-IWD-07 Step 3, BW-IWD-08 Step 3; CW-IWD-02)
- UC-IWD-071: Coordinate Procurement for Stock Shortage (BW-IWD-07 Steps 1-2, BW-IWD-08 Steps 1-2; CW-IWD-02)
- BR-IWD-001: Active-role authorization isolation (IWD Admin only)
- BR-IWD-004: Low-cost internal quotation procurement route
- BR-IWD-008: Policy-compliant mid-range procurement coordination
- BR-IWD-010: Inventory check before procurement initiation
- BR-IWD-011: Material usage and inventory movements auditable trail
- BR-IWD-013: Append-only audit logging in ComplaintTransition
- CFR-IWD-09 (AFR-IWD-027 through AFR-IWD-031)
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.iwd.domain.cost_bands import CostBand, classify_cost_band
from modules.iwd.domain.state_machine import IWDState, transition_inventory_and_procurement
from modules.iwd.models import Complaint, ComplaintTransition, MaterialIssue


def _validate_iwd_admin(principal) -> None:
    """Enforce active role 'iwd_admin' and permission 'iwd.inventory.manage'."""
    if principal is None or getattr(principal, "active_role", None) != "iwd_admin":
        raise PermissionDeniedError(
            "An active role of 'iwd_admin' is required for inventory and procurement actions.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.inventory.manage"):
        raise PermissionDeniedError(
            "Permission 'iwd.inventory.manage' is required.",
            code="permission_denied",
        )


def issue_stock_material(
    *,
    complaint_id: int,
    principal,
    materials_summary: str,
    remarks: str = "",
) -> tuple[Complaint, MaterialIssue]:
    """Issue available warehouse stock for an estimate-approved complaint (BW-IWD-06 Step 1 / UC-IWD-061).

    Transitions: ESTIMATE_APPROVED -> MATERIALS_ISSUED
    Persists: MaterialIssue(source='stock') and append-only ComplaintTransition
    """
    _validate_iwd_admin(principal)

    summary_str = materials_summary.strip() if materials_summary else ""
    if not summary_str:
        raise BadRequestError(
            "Materials summary with quantities is required when issuing stock materials (AFR-IWD-029, BR-IWD-011).",
            code="missing_materials_summary",
        )

    remarks_str = remarks.strip() if remarks else ""

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status != IWDState.ESTIMATE_APPROVED.value:
            raise ConflictError(
                f"Cannot issue stock materials for complaint in status '{complaint.status}'. "
                f"Complaint must be in '{IWDState.ESTIMATE_APPROVED.value}'.",
                code="invalid_state_transition",
            )

        # High-cost works use external bidding (BR-IWD-007) and cannot use internal stock issuance
        latest_estimate = complaint.estimates.order_by("-created_at").first()
        if latest_estimate and latest_estimate.estimated_cost > Decimal("250000.00"):
            raise ConflictError(
                "High-cost works (> ₹2.5L) use external bidding (BR-IWD-007) and cannot issue warehouse materials.",
                code="high_cost_bidding_required",
            )

        next_state = transition_inventory_and_procurement(
            current_state=IWDState.ESTIMATE_APPROVED,
            action="issue_stock",
            actor_role="IWD Admin",
        )

        issue_record = MaterialIssue.objects.create(
            complaint=complaint,
            admin_user_id=principal.user_id,
            source="stock",
            materials_summary=summary_str,
            remarks=remarks_str,
        )

        from_status = complaint.status
        complaint.status = next_state.value
        complaint.save(update_fields=["status", "updated_at"])

        reason_text = f"Stock materials issued: {summary_str}"
        if remarks_str:
            reason_text = f"{reason_text} ({remarks_str})"

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=next_state.value,
            actor_user_id=principal.user_id,
            actor_label="IWD Admin",
            reason=reason_text,
        )

    return complaint, issue_record


def record_stock_shortage(
    *,
    complaint_id: int,
    principal,
    remarks: str = "",
) -> Complaint:
    """Record stock shortage and initiate procurement coordination (BW-IWD-07 Step 1, BW-IWD-08 Step 1 / UC-IWD-071).

    Transitions:
    - Low-Cost (< ₹25,000): ESTIMATE_APPROVED -> PROCUREMENT_NEEDED_LOW
    - Mid-Range (₹25,000 - ₹2,50,000): ESTIMATE_APPROVED -> PROCUREMENT_NEEDED_MID
    """
    _validate_iwd_admin(principal)
    remarks_str = remarks.strip() if remarks else ""

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status != IWDState.ESTIMATE_APPROVED.value:
            raise ConflictError(
                f"Cannot record stock shortage for complaint in status '{complaint.status}'. "
                f"Complaint must be in '{IWDState.ESTIMATE_APPROVED.value}'.",
                code="invalid_state_transition",
            )

        latest_estimate = complaint.estimates.order_by("-created_at").first()
        if not latest_estimate:
            raise ConflictError(
                "No estimate found for approved complaint to determine procurement cost band.",
                code="missing_estimate",
            )

        if latest_estimate.estimated_cost > Decimal("250000.00"):
            raise ConflictError(
                "High-cost works (> ₹2.5L) use external bidding (BR-IWD-007) and cannot use inventory stock shortage procurement.",
                code="high_cost_bidding_required",
            )

        cost_band = classify_cost_band(latest_estimate.estimated_cost)

        next_state = transition_inventory_and_procurement(
            current_state=IWDState.ESTIMATE_APPROVED,
            action="stock_unavailable",
            actor_role="IWD Admin",
            cost_band=cost_band,
        )

        from_status = complaint.status
        complaint.status = next_state.value
        complaint.save(update_fields=["status", "updated_at"])

        reason_text = remarks_str or f"Stock shortage identified for {cost_band.value} work; procurement coordination initiated"

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=next_state.value,
            actor_user_id=principal.user_id,
            actor_label="IWD Admin",
            reason=reason_text,
        )

    return complaint


def complete_procurement(
    *,
    complaint_id: int,
    principal,
    remarks: str = "",
) -> Complaint:
    """Record that procurement coordination has made required materials available (BW-IWD-07 Step 2, BW-IWD-08 Step 2 / UC-IWD-071).

    Transitions:
    - PROCUREMENT_NEEDED_LOW -> MATERIALS_AVAILABLE
    - PROCUREMENT_NEEDED_MID -> MATERIALS_AVAILABLE
    """
    _validate_iwd_admin(principal)
    remarks_str = remarks.strip() if remarks else ""

    allowed_states = (
        IWDState.PROCUREMENT_NEEDED_LOW.value,
        IWDState.PROCUREMENT_NEEDED_MID.value,
    )

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status not in allowed_states:
            raise ConflictError(
                f"Cannot complete procurement for complaint in status '{complaint.status}'. "
                f"Complaint must be in one of {allowed_states}.",
                code="invalid_state_transition",
            )

        next_state = transition_inventory_and_procurement(
            current_state=IWDState(complaint.status),
            action="procurement_complete",
            actor_role="IWD Admin",
        )

        from_status = complaint.status
        complaint.status = next_state.value
        complaint.save(update_fields=["status", "updated_at"])

        reason_text = remarks_str or "Procurement coordination completed; materials available"

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=next_state.value,
            actor_user_id=principal.user_id,
            actor_label="IWD Admin",
            reason=reason_text,
        )

    return complaint


def issue_procured_material(
    *,
    complaint_id: int,
    principal,
    materials_summary: str,
    remarks: str = "",
) -> tuple[Complaint, MaterialIssue]:
    """Issue procured materials for approved work (BW-IWD-07 Step 3, BW-IWD-08 Step 3 / UC-IWD-061).

    Transitions: MATERIALS_AVAILABLE -> MATERIALS_ISSUED
    Persists: MaterialIssue(source='procurement') and append-only ComplaintTransition
    """
    _validate_iwd_admin(principal)

    summary_str = materials_summary.strip() if materials_summary else ""
    if not summary_str:
        raise BadRequestError(
            "Materials summary with quantities is required when issuing procured materials (AFR-IWD-029, BR-IWD-011).",
            code="missing_materials_summary",
        )

    remarks_str = remarks.strip() if remarks else ""

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.status != IWDState.MATERIALS_AVAILABLE.value:
            raise ConflictError(
                f"Cannot issue procured materials for complaint in status '{complaint.status}'. "
                f"Complaint must be in '{IWDState.MATERIALS_AVAILABLE.value}'.",
                code="invalid_state_transition",
            )

        next_state = transition_inventory_and_procurement(
            current_state=IWDState.MATERIALS_AVAILABLE,
            action="issue_material",
            actor_role="IWD Admin",
        )

        issue_record = MaterialIssue.objects.create(
            complaint=complaint,
            admin_user_id=principal.user_id,
            source="procurement",
            materials_summary=summary_str,
            remarks=remarks_str,
        )

        from_status = complaint.status
        complaint.status = next_state.value
        complaint.save(update_fields=["status", "updated_at"])

        reason_text = f"Procured materials issued: {summary_str}"
        if remarks_str:
            reason_text = f"{reason_text} ({remarks_str})"

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=next_state.value,
            actor_user_id=principal.user_id,
            actor_label="IWD Admin",
            reason=reason_text,
        )

    return complaint, issue_record


def execute_inventory_action(
    *,
    complaint_id: int,
    principal,
    action: str,
    materials_summary: str = "",
    remarks: str = "",
) -> tuple[Complaint, MaterialIssue | None]:
    """Dispatch inventory verification, procurement, or material issuance actions."""
    if action == "issue_stock":
        complaint, issue = issue_stock_material(
            complaint_id=complaint_id,
            principal=principal,
            materials_summary=materials_summary,
            remarks=remarks,
        )
        return complaint, issue

    if action == "stock_unavailable":
        complaint = record_stock_shortage(
            complaint_id=complaint_id,
            principal=principal,
            remarks=remarks,
        )
        return complaint, None

    if action == "procurement_complete":
        complaint = complete_procurement(
            complaint_id=complaint_id,
            principal=principal,
            remarks=remarks,
        )
        return complaint, None

    if action in ("issue_material", "issue_procured"):
        complaint, issue = issue_procured_material(
            complaint_id=complaint_id,
            principal=principal,
            materials_summary=materials_summary,
            remarks=remarks,
        )
        return complaint, issue

    raise BadRequestError(
        f"Invalid inventory action '{action}'. "
        f"Must be one of: 'issue_stock', 'stock_unavailable', 'procurement_complete', 'issue_material'.",
        code="invalid_inventory_action",
    )

