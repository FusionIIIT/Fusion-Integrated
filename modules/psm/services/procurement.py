# External procurement method selection and PO issuance/tracking (PSM-UC-025, 026, 027).
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import approval_policy as ap
from modules.psm.domain import state_machine as sm
from modules.psm.domain.vendor_rules import ensure_vendor_verified
from modules.psm.models import Indent, PurchaseOrder, Tender, Vendor
from modules.psm.services.common import (
    audit_record,
    enqueue_notification,
    next_number,
    policy_to_spec,
    require_active_policy,
    translate_errors,
)
from modules.psm.services.indents import transition_indent


@transaction.atomic
def review_and_select_method(*, actor, indent_id: int, notes: str = "") -> Indent:
    """Select direct/tender method and route high-value indents (PSM-UC-025)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    with translate_errors():
        ap.ensure_not_self_approval(indent.user_id, actor.user_id)
        method = ap.select_procurement_method(indent.estimated_cost, spec)
    needs_final = ap.requires_final_approval(indent.estimated_cost, spec)
    if indent.status == sm.DEPARTMENT_REVIEWED:
        if not ap.allows_high_priority_direct_path(indent.priority, indent.estimated_cost, spec):
            raise ConflictError(
                "Department Head recommendation is required before PS Admin review.",
                code="hod_review_required",
            )
        target_status = sm.PROCUREMENT_AUTHORIZED
    else:
        target_status = sm.AWAITING_FINAL_APPROVAL if needs_final else sm.PROCUREMENT_AUTHORIZED
    transition_indent(
        indent=indent,
        to_status=target_status,
        actor=actor,
        actor_lane=sm.PS_ADMIN,
        action="indent.procurement_reviewed",
        reason=notes.strip() or f"Procurement method selected: {method}",
        extra_updates={"procurement_method": method},
    )
    enqueue_notification(
        topic="indent.procurement_reviewed",
        dedupe_key=f"indent.ps_review:{indent.pk}:{target_status}",
        recipient_user_id=indent.user_id,
        subject=f"Indent {indent.indent_number} procurement review complete",
        body=f"Procurement method '{method}' selected; status is now {target_status}.",
        payload={"indent_id": indent.pk, "method": method, "status": target_status},
    )
    return indent


def _resolve_po_authorization(
    indent: Indent, vendor: Vendor, tender_id: int | None
) -> Tender | None:
    """Verify indent approval state and matching tender award for PO issuance."""
    if indent.procurement_method == "tender":
        if indent.status != sm.TENDER_AWARDED:
            raise ConflictError(
                "Complete tender evaluation and committee award before issuing a PO.",
                code="tender_not_awarded",
            )
        qs = Tender.objects.filter(indent=indent, status=sm.TENDER_AWARDED_STATE)
        tender = qs.filter(pk=tender_id).first() if tender_id else qs.first()
        if tender is None or tender.awarded_vendor_id != vendor.pk:
            raise ConflictError(
                "PO vendor must match the committee-awarded tender vendor.",
                code="vendor_mismatch_tender",
            )
        return tender
    if indent.status != sm.PROCUREMENT_AUTHORIZED or indent.procurement_method != "direct":
        raise ConflictError(
            "Indent has not completed required approvals for direct PO issuance.",
            code="indent_not_authorized",
        )
    return None


def _finalize_po_issuance(actor, indent: Indent, vendor: Vendor, po: PurchaseOrder) -> None:
    """Transition indent, record audit entry, and notify requestor on PO issuance."""
    transition_indent(
        indent=indent,
        to_status=sm.PO_ISSUED,
        actor=actor,
        actor_lane=sm.PS_ADMIN,
        action="po.issued",
        reason=f"Purchase Order {po.po_number} issued to {vendor.name}",
    )
    audit_record(
        actor=actor,
        action="po.issued",
        target_type="purchase_order",
        target_id=po.pk,
        to_state=sm.PO_ISSUED,
    )
    enqueue_notification(
        topic="po.issued",
        dedupe_key=f"po.issued:{po.pk}",
        recipient_user_id=indent.user_id,
        subject=f"Purchase Order {po.po_number} issued",
        body=f"PO {po.po_number} issued to {vendor.name}; delivery {po.planned_delivery_date}.",
        payload={"po_id": po.pk, "indent_id": indent.pk},
    )


@transaction.atomic
def create_and_issue_po(
    *,
    actor,
    indent_id: int,
    vendor_id: int,
    unit_price: Decimal,
    planned_delivery_date: date,
    ordered_quantity: int | None = None,
    tender_id: int | None = None,
    delivery_notes: str = "",
) -> PurchaseOrder:
    """Create and issue a PO after approvals and vendor verification (PSM-UC-026)."""
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    vendor = Vendor.objects.filter(pk=vendor_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    with translate_errors():
        ensure_vendor_verified(
            vendor_name=vendor.name,
            is_verified=vendor.is_verified,
            is_active=vendor.is_active,
            action="issue a purchase order",
        )
    tender = _resolve_po_authorization(indent, vendor, tender_id)
    qty = ordered_quantity if ordered_quantity is not None else indent.quantity
    if qty <= 0 or unit_price <= Decimal("0"):
        raise DomainError(
            "Ordered quantity and unit price must be greater than zero.", code="invalid_po_amounts"
        )
    po = PurchaseOrder.objects.create(
        po_number=next_number("PO"),
        indent=indent,
        vendor=vendor,
        tender=tender,
        ordered_quantity=qty,
        unit_price=unit_price,
        total_amount=(Decimal(qty) * unit_price).quantize(Decimal("0.01")),
        status=sm.PO_ISSUED,
        planned_delivery_date=planned_delivery_date,
        delivery_notes=delivery_notes.strip(),
        issued_by_user_id=actor.user_id,
    )
    _finalize_po_issuance(actor, indent, vendor, po)
    return po


def _notify_po_status_change(po: PurchaseOrder, old_status: str) -> None:
    """Enqueue requestor notification when a PO status changes."""
    if po.status == old_status:
        return
    enqueue_notification(
        topic="po.status_changed",
        dedupe_key=f"po.status:{po.pk}:{po.status}:{po.updated_at.isoformat()}",
        recipient_user_id=po.indent.user_id,
        subject=f"PO {po.po_number} status updated to {po.status}",
        body=f"Purchase order {po.po_number} is now '{po.status}'.",
        payload={"po_id": po.pk, "status": po.status},
    )


@transaction.atomic
def update_po_schedule(
    *,
    actor,
    po_id: int,
    status: str | None = None,
    planned_delivery_date: date | None = None,
    actual_delivery_date: date | None = None,
    delivery_notes: str | None = None,
) -> PurchaseOrder:
    """Update PO delivery status and schedule centrally (PSM-UC-027, AFR-PSM-041, AFR-PSM-042)."""
    po = PurchaseOrder.objects.select_for_update().select_related("indent").filter(pk=po_id).first()
    if po is None:
        raise NotFoundError("Purchase order not found.")
    if po.status in sm.PO_TERMINAL:
        raise ConflictError(
            f"Cannot modify a purchase order that is already '{po.status}'.", code="po_terminal"
        )
    old_status = po.status
    if status is not None and status != po.status:
        with translate_errors():
            sm.resolve("purchase_order", po.status, status, sm.PS_ADMIN)
        po.status = status
    if planned_delivery_date is not None:
        po.planned_delivery_date = planned_delivery_date
    if actual_delivery_date is not None:
        po.actual_delivery_date = actual_delivery_date
    if delivery_notes is not None:
        po.delivery_notes = delivery_notes.strip()
    po.save()
    audit_record(
        actor=actor,
        action="po.schedule_updated",
        target_type="purchase_order",
        target_id=po.pk,
        from_state=old_status,
        to_state=po.status,
    )
    _notify_po_status_change(po, old_status)
    return po
