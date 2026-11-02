"""Writes for the purchase-indent, stock, PO, receipt, invoice and transfer lifecycles."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import models, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.purchase_stores.domain.workflow import (
    IndentStatus,
    InvalidTransition,
    validate_transition,
)
from modules.purchase_stores.models import (
    DepartmentAccess,
    DiscrepancyCase,
    GoodsReceipt,
    Indent,
    IndentLine,
    IndentVersion,
    PolicySetting,
    PurchaseOrder,
    StockBalance,
    StockLedgerEntry,
    StockReservation,
    StockTransfer,
    StockTransferReservation,
    Vendor,
    VendorInvoice,
    VendorPayment,
    WorkflowAction,
)


def _require(actor, permission):
    if not actor.has_permission(permission):
        raise PermissionDeniedError(f"This action needs {permission}.")


def _has_department_access(actor, department_id):
    return (
        actor.has_permission("purchase_stores.policy.manage")
        or actor.has_permission("purchase_stores.po.manage")
        or DepartmentAccess.objects.filter(
            user_id=actor.user_id, department_id=department_id, is_active=True
        ).exists()
    )


def _reference(prefix):
    return f"{prefix}-{timezone.now():%Y%m%d}-{uuid4().hex[:8].upper()}"


def _item_key(line):
    sku = str(line.get("sku", "")).strip().casefold()
    if sku:
        return f"sku:{sku}"
    name = " ".join(str(line.get("item_name", "")).casefold().split())
    return f"item:{name}"


def _stock_sku(line):
    sku = str(line.get("sku", "")).strip()
    if sku:
        return sku
    normalized = " ".join(str(line.get("item_name", "")).upper().split())
    return f"ITEM:{normalized[:74]}"


def _snapshot(indent):
    return {
        "reference": indent.reference,
        "requestor_user_id": indent.requestor_user_id,
        "department_id": indent.department_id,
        "justification": indent.justification,
        "priority": indent.priority,
        "lines": list(
            indent.lines.values(
                "item_name", "description", "quantity", "unit", "estimated_unit_cost", "sku"
            )
        ),
    }


@transaction.atomic
def create_indent(*, actor, department_id, justification, lines, draft=False, priority=""):
    _require(actor, "purchase_stores.indent.create")
    if (
        not actor.has_permission("purchase_stores.policy.manage")
        and not DepartmentAccess.objects.filter(
            user_id=actor.user_id, department_id=department_id, is_active=True
        ).exists()
    ):
        raise PermissionDeniedError("You are not assigned to create indents for this department.")
    indent = Indent.objects.create(
        reference=_reference("PSM"),
        requestor_user_id=actor.user_id,
        department_id=department_id,
        justification=justification,
        priority=priority,
        status=Indent.Status.DRAFT if draft else Indent.Status.SUBMITTED,
        submitted_at=None if draft else timezone.now(),
    )
    IndentLine.objects.bulk_create([IndentLine(indent=indent, **line) for line in lines])
    IndentVersion.objects.create(
        indent=indent, version=1, actor_user_id=actor.user_id, snapshot=_snapshot(indent)
    )
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="CREATED" if draft else "SUBMITTED",
        to_status=indent.status,
    )
    if not draft:
        indent.duplicate_of_id = _potential_duplicate(indent)
        indent.duplicate_review_required = indent.duplicate_of_id is not None
        if indent.duplicate_review_required:
            indent.save(
                update_fields=["duplicate_of_id", "duplicate_review_required", "updated_at"]
            )
    return indent


def _potential_duplicate(indent):
    item_keys = {_item_key(line) for line in indent.lines.values("sku", "item_name")}
    if not item_keys:
        return None
    active_statuses = [
        Indent.Status.DRAFT,
        Indent.Status.SUBMITTED,
        Indent.Status.STOCK_RESERVED,
        Indent.Status.EXTERNAL_PROCUREMENT_REQUIRED,
        Indent.Status.DEPARTMENT_REVIEWED,
        Indent.Status.DEPARTMENT_HEAD_RECOMMENDED,
        Indent.Status.AWAITING_FINAL_APPROVAL,
        Indent.Status.PROCUREMENT_AUTHORIZED,
    ]
    for other in (
        Indent.objects.filter(
            requestor_user_id=indent.requestor_user_id,
            department_id=indent.department_id,
            status__in=active_statuses,
        )
        .exclude(pk=indent.pk)
        .prefetch_related("lines")
    ):
        other_keys = {_item_key(line) for line in other.lines.values("sku", "item_name")}
        if item_keys.intersection(other_keys):
            return other.pk
    return None


@transaction.atomic
def modify_indent(*, actor, indent_id, justification, lines):
    _require(actor, "purchase_stores.indent.create")
    indent = (
        Indent.objects.select_for_update()
        .filter(pk=indent_id, requestor_user_id=actor.user_id)
        .first()
    )
    if indent is None:
        raise NotFoundError("No purchase indent was found.")
    if indent.status not in {
        Indent.Status.DRAFT,
        Indent.Status.SUBMITTED,
        Indent.Status.DEPARTMENT_REVIEWED,
    }:
        raise ConflictError("This indent cannot be changed in its current state.")
    previous = indent.status
    IndentLine.objects.filter(indent=indent).delete()
    IndentLine.objects.bulk_create([IndentLine(indent=indent, **line) for line in lines])
    indent.justification = justification
    indent.current_version += 1
    indent.status = Indent.Status.SUBMITTED
    indent.submitted_at = timezone.now()
    indent.save(
        update_fields=["justification", "current_version", "status", "submitted_at", "updated_at"]
    )
    indent.duplicate_of_id = _potential_duplicate(indent)
    indent.duplicate_review_required = indent.duplicate_of_id is not None
    indent.save(update_fields=["duplicate_of_id", "duplicate_review_required", "updated_at"])
    IndentVersion.objects.create(
        indent=indent,
        version=indent.current_version,
        actor_user_id=actor.user_id,
        snapshot=_snapshot(indent),
    )
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="MODIFIED",
        from_status=previous,
        to_status=indent.status,
    )
    return indent


@transaction.atomic
def transition_indent(*, actor, indent_id, to_status, reason="", priority=""):
    target = IndentStatus(to_status)
    if target == IndentStatus.REJECTED:
        _require(actor, "purchase_stores.indent.review")
    elif target in {IndentStatus.WITHDRAWN, IndentStatus.CANCELLED}:
        _require(actor, "purchase_stores.indent.withdraw")
    else:
        _require(actor, "purchase_stores.indent.review")
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("No purchase indent was found.")
    if (
        indent.requestor_user_id != actor.user_id
        and not _has_department_access(actor, indent.department_id)
        and not (
            target == IndentStatus.PROCUREMENT_AUTHORIZED
            and indent.status == Indent.Status.AWAITING_FINAL_APPROVAL
            and "director" in {role.lower() for role in actor.roles}
        )
    ):
        raise PermissionDeniedError(
            "You are not assigned to this department's procurement workflow."
        )
    if target == IndentStatus.PROCUREMENT_AUTHORIZED:
        threshold = policy_value("final_approval_threshold")
        if threshold is None:
            raise ConflictError(
                "Configure final_approval_threshold before authorizing procurement.",
                code="policy_not_configured",
            )
        amount = sum(
            (line.quantity * line.estimated_unit_cost for line in indent.lines.all()), Decimal("0")
        )
        roles = {role.lower() for role in actor.roles}
        final_authority = bool(roles.intersection({"director", "registrar"}))
        if amount >= Decimal(str(threshold)):
            if indent.status != Indent.Status.AWAITING_FINAL_APPROVAL or not final_authority:
                raise PermissionDeniedError(
                    "This indent requires Director/Registrar approval under configured policy."
                )
        elif indent.status == Indent.Status.AWAITING_FINAL_APPROVAL or not actor.has_permission(
            "purchase_stores.po.manage"
        ):
            raise PermissionDeniedError(
                "Only procurement staff may authorize this indent under configured policy."
            )
    if (
        target in {IndentStatus.WITHDRAWN, IndentStatus.CANCELLED}
        and indent.requestor_user_id != actor.user_id
    ):
        _require(actor, "purchase_stores.indent.review")
    try:
        validate_transition(indent.status, target, reason)
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_indent_transition") from exc
    previous = indent.status
    indent.status = target
    if priority:
        indent.priority = priority
    indent.save(update_fields=["status", "priority", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action=target.value,
        from_status=previous,
        to_status=target.value,
        reason=reason,
    )
    return indent


@transaction.atomic
def check_and_reserve_stock(*, actor, indent_id):
    _require(actor, "purchase_stores.stock.manage")
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("No purchase indent was found.")
    if not _has_department_access(actor, indent.department_id):
        raise PermissionDeniedError("You are not assigned to this department's stock records.")
    if indent.status != Indent.Status.SUBMITTED:
        raise ConflictError("Stock can only be reserved for a submitted indent.")
    lines = list(indent.lines.all())
    balances = {}
    sufficient = True
    for line in lines:
        if not line.sku:
            sufficient = False
            break
        rows = (
            StockBalance.objects.select_for_update()
            .filter(sku=line.sku)
            .filter(
                models.Q(department_id=indent.department_id, is_central=False)
                | models.Q(is_central=True)
            )
            .order_by("is_central", "id")
        )
        available = sum((row.quantity_available for row in rows), Decimal("0"))
        if available < line.quantity:
            sufficient = False
            break
        balances[line.pk] = list(rows)
    if sufficient:
        for line in lines:
            remaining = line.quantity
            for balance in balances[line.pk]:
                reserve = min(remaining, balance.quantity_available)
                if reserve <= 0:
                    continue
                balance.quantity_reserved += reserve
                balance.save(update_fields=["quantity_reserved", "updated_at"])
                StockReservation.objects.create(indent_line=line, stock=balance, quantity=reserve)
                remaining -= reserve
                if remaining == 0:
                    break
        target = IndentStatus.STOCK_RESERVED
    else:
        target = IndentStatus.EXTERNAL_PROCUREMENT_REQUIRED
    previous = indent.status
    validate_transition(previous, target)
    indent.status = target
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="STOCK_CHECKED",
        from_status=previous,
        to_status=target,
        details={"sufficient": sufficient},
    )
    return indent


@transaction.atomic
def process_internal_issue(*, actor, indent_id):
    _require(actor, "purchase_stores.stock.manage")
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("No purchase indent was found.")
    if not _has_department_access(actor, indent.department_id):
        raise PermissionDeniedError("You are not assigned to this department's stock records.")
    if indent.status != Indent.Status.INTERNAL_ISSUE_APPROVED:
        raise ConflictError("The indent is not approved for internal issue.")
    if not indent.lines.filter(reservations__status=StockReservation.Status.RESERVED).exists():
        raise ConflictError("Internal issue requires active stock reservations.")
    indent.status = Indent.Status.DISPATCHED_READY_FOR_RECEIPT
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="INTERNAL_STOCK_DISPATCHED",
        from_status=Indent.Status.INTERNAL_ISSUE_APPROVED,
        to_status=indent.status,
    )
    return indent


@transaction.atomic
def confirm_internal_receipt(*, actor, indent_id, reason=""):
    _require(actor, "purchase_stores.indent.create")
    indent = (
        Indent.objects.select_for_update()
        .filter(pk=indent_id, requestor_user_id=actor.user_id)
        .first()
    )
    if indent is None:
        raise NotFoundError("No purchase indent was found.")
    if indent.status != Indent.Status.DISPATCHED_READY_FOR_RECEIPT:
        raise ConflictError("There is no dispatched internal issue awaiting receipt confirmation.")
    reservations = list(
        StockReservation.objects.select_for_update()
        .filter(indent_line__indent=indent, status=StockReservation.Status.RESERVED)
        .select_related("stock")
    )
    if not reservations:
        raise ConflictError("No active stock reservation was found for this indent.")
    for reservation in reservations:
        stock = reservation.stock
        if (
            stock.quantity_on_hand < reservation.quantity
            or stock.quantity_reserved < reservation.quantity
        ):
            raise ConflictError("Reserved stock changed before receipt confirmation.")
        stock.quantity_on_hand -= reservation.quantity
        stock.quantity_reserved -= reservation.quantity
        stock.save(update_fields=["quantity_on_hand", "quantity_reserved", "updated_at"])
        reservation.status = StockReservation.Status.CONSUMED
        reservation.save(update_fields=["status", "updated_at"])
        StockLedgerEntry.objects.create(
            stock=stock,
            kind=StockLedgerEntry.Kind.ISSUE,
            quantity_delta=-reservation.quantity,
            reference=indent.reference,
            actor_user_id=actor.user_id,
            note="Confirmed internal stock issue",
        )
    previous = indent.status
    validate_transition(previous, Indent.Status.RECEIPT_CONFIRMED)
    indent.status = Indent.Status.RECEIPT_CONFIRMED
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="INTERNAL_RECEIPT_CONFIRMED",
        from_status=previous,
        to_status=indent.status,
        reason=reason,
    )
    return indent


@transaction.atomic
def create_vendor(*, actor, data):
    _require(actor, "purchase_stores.vendor.manage")
    vendor = Vendor.objects.create(**data)
    from modules.purchase_stores.models import VendorVersion

    VendorVersion.objects.create(
        vendor=vendor, version=1, actor_user_id=actor.user_id, snapshot=data
    )
    return vendor


@transaction.atomic
def issue_purchase_order(*, actor, indent_id, vendor_id, total_amount, planned_delivery_at=None):
    _require(actor, "purchase_stores.po.manage")
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("No purchase indent was found.")
    vendor = Vendor.objects.filter(pk=vendor_id, status=Vendor.Status.VERIFIED).first()
    if vendor is None:
        raise ConflictError(
            "Purchase orders require a verified vendor.", code="vendor_not_verified"
        )
    if indent.status != Indent.Status.PROCUREMENT_AUTHORIZED:
        raise ConflictError("The indent has not completed required approvals.")
    threshold = policy_value("procurement_method_threshold")
    if threshold is None:
        raise ConflictError(
            "Configure procurement_method_threshold before issuing purchase orders.",
            code="policy_not_configured",
        )
    tender_required = sum(
        (line.quantity * line.estimated_unit_cost for line in indent.lines.all()), Decimal("0")
    ) >= Decimal(str(threshold))
    selected_tender = (
        indent.tenders.filter(status="AWARDED", selected_bid__isnull=False)
        .select_related("selected_bid")
        .first()
    )
    if tender_required and (
        selected_tender is None or selected_tender.selected_bid.vendor_id != vendor.pk
    ):
        raise ConflictError(
            "A committee-approved tender bid is required by the configured procurement threshold."
        )
    if not tender_required and selected_tender is not None:
        raise ConflictError(
            "This indent is below the configured tender threshold and must use direct procurement."
        )
    order = PurchaseOrder.objects.create(
        reference=_reference("PO"),
        indent=indent,
        vendor=vendor,
        total_amount=total_amount,
        line_items=list(indent.lines.values("item_name", "quantity", "estimated_unit_cost", "sku")),
        planned_delivery_at=planned_delivery_at,
    )
    previous = indent.status
    indent.status = Indent.Status.PO_ISSUED
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="PO_ISSUED",
        from_status=previous,
        to_status=indent.status,
        details={"purchase_order_id": order.pk},
    )
    return order


@transaction.atomic
def record_goods_receipt(
    *, actor, purchase_order_id, accepted_lines, rejected_lines=None, discrepancy_note=""
):
    _require(actor, "purchase_stores.receipt.manage")
    order = PurchaseOrder.objects.select_for_update().filter(pk=purchase_order_id).first()
    if order is None:
        raise NotFoundError("No purchase order was found.")
    if not _has_department_access(actor, order.indent.department_id):
        raise PermissionDeniedError("You are not assigned to inspect receipts for this department.")
    if order.status not in {
        PurchaseOrder.Status.ISSUED,
        PurchaseOrder.Status.ACKNOWLEDGED,
        PurchaseOrder.Status.PARTIALLY_DELIVERED,
        PurchaseOrder.Status.DELIVERED,
    }:
        raise ConflictError("This purchase order cannot receive goods in its current state.")
    ordered_by_sku = {}
    for line in order.line_items:
        key = _item_key(line)
        ordered_by_sku[key] = ordered_by_sku.get(key, Decimal("0")) + Decimal(str(line["quantity"]))
    received_by_sku = {}
    for prior in order.receipts.all():
        for line in prior.accepted_lines:
            key = _item_key(line)
            received_by_sku[key] = received_by_sku.get(key, Decimal("0")) + Decimal(
                str(line.get("quantity", "0"))
            )
    for line in accepted_lines:
        key = _item_key(line)
        quantity = Decimal(str(line.get("quantity", "0")))
        if key not in ordered_by_sku or quantity <= 0:
            raise ConflictError(
                "Accepted receipt lines must match a purchase-order SKU and quantity."
            )
        received_by_sku[key] = received_by_sku.get(key, Decimal("0")) + quantity
        if received_by_sku[key] > ordered_by_sku[key]:
            raise ConflictError("Accepted receipt quantity exceeds the purchase-order quantity.")
    for line in rejected_lines or []:
        if _item_key(line) not in ordered_by_sku or Decimal(str(line.get("quantity", "0"))) <= 0:
            raise ConflictError(
                "Rejected receipt lines must match a purchase-order SKU and quantity."
            )
    receipt = GoodsReceipt.objects.create(
        purchase_order=order,
        receipt_reference=_reference("GRN"),
        inspected_by_user_id=actor.user_id,
        accepted_lines=accepted_lines,
        rejected_lines=rejected_lines or [],
        discrepancy_note=discrepancy_note,
    )
    indent = Indent.objects.select_for_update().get(pk=order.indent_id)
    accepted = bool(accepted_lines)
    rejected = bool(rejected_lines)
    if indent.status == Indent.Status.PO_ISSUED:
        validate_transition(indent.status, Indent.Status.DELIVERED)
        WorkflowAction.objects.create(
            indent=indent,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            action="DELIVERED",
            from_status=indent.status,
            to_status=Indent.Status.DELIVERED,
        )
        indent.status = Indent.Status.DELIVERED
    if rejected:
        validate_transition(indent.status, Indent.Status.DISCREPANCY_IDENTIFIED)
        previous = indent.status
        indent.status = Indent.Status.DISCREPANCY_IDENTIFIED
        DiscrepancyCase.objects.create(
            goods_receipt=receipt,
            description=discrepancy_note or "Rejected or damaged goods were recorded.",
            evidence=[],
        )
        WorkflowAction.objects.create(
            indent=indent,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            action="DISCREPANCY_CASE_OPENED",
            from_status=indent.status,
            to_status=Indent.Status.DISCREPANCY_CASE_OPEN,
        )
        validate_transition(indent.status, Indent.Status.DISCREPANCY_CASE_OPEN)
        indent.status = Indent.Status.DISCREPANCY_CASE_OPEN
    elif accepted:
        previous = indent.status
        fully_received = bool(ordered_by_sku) and all(
            received_by_sku.get(sku, Decimal("0")) >= quantity
            for sku, quantity in ordered_by_sku.items()
        )
        if previous == Indent.Status.REPLACEMENT_AWAITED:
            indent.status = Indent.Status.REPLACEMENT_CONFIRMED
        else:
            indent.status = (
                Indent.Status.GRN_ACCEPTED if fully_received else Indent.Status.GRN_PARTIAL
            )
        validate_transition(previous, indent.status)
        order.status = (
            PurchaseOrder.Status.DELIVERED
            if fully_received
            else PurchaseOrder.Status.PARTIALLY_DELIVERED
        )
        order.actual_delivery_at = timezone.now()
        order.save(update_fields=["status", "actual_delivery_at", "updated_at"])
    else:
        raise ConflictError("A goods receipt must include accepted or rejected quantities.")
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="GRN_RECORDED",
        from_status=previous,
        to_status=indent.status,
        details={"goods_receipt_id": receipt.pk},
    )
    return receipt


@transaction.atomic
def confirm_goods_receipt(*, actor, receipt_id):
    _require(actor, "purchase_stores.indent.create")
    receipt = (
        GoodsReceipt.objects.select_for_update()
        .select_related("purchase_order__indent")
        .filter(purchase_order__indent__requestor_user_id=actor.user_id, pk=receipt_id)
        .first()
    )
    if receipt is None:
        raise NotFoundError("No receipt was found.")
    if receipt.confirmed_at is not None:
        raise ConflictError("This goods receipt has already been confirmed.")
    if receipt.discrepancies.filter(
        status__in=[
            DiscrepancyCase.Status.OPEN,
            DiscrepancyCase.Status.RETURN,
            DiscrepancyCase.Status.REPLACEMENT,
            DiscrepancyCase.Status.WARRANTY,
        ]
    ).exists():
        raise ConflictError("Resolve the receipt discrepancy before confirming receipt.")
    receipt.receipt_confirmed_by_user_id = actor.user_id
    receipt.confirmed_at = timezone.now()
    receipt.save(update_fields=["receipt_confirmed_by_user_id", "confirmed_at", "updated_at"])
    indent = receipt.purchase_order.indent
    for line in receipt.accepted_lines:
        sku = _stock_sku(line)
        quantity = Decimal(str(line.get("quantity", "0")))
        if not sku or quantity <= 0:
            raise ConflictError("Accepted receipt lines require a SKU and positive quantity.")
        stock, _ = StockBalance.objects.select_for_update().get_or_create(
            sku=sku,
            department_id=indent.department_id,
            is_central=False,
            defaults={"item_name": line.get("item_name", sku)},
        )
        stock.quantity_on_hand += quantity
        stock.save(update_fields=["quantity_on_hand", "updated_at"])
        StockLedgerEntry.objects.create(
            stock=stock,
            kind=StockLedgerEntry.Kind.RECEIPT,
            quantity_delta=quantity,
            reference=receipt.receipt_reference,
            actor_user_id=actor.user_id,
            note="Accepted goods receipt",
        )
    previous = indent.status
    validate_transition(previous, Indent.Status.RECEIPT_CONFIRMED)
    indent.status = Indent.Status.RECEIPT_CONFIRMED
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="RECEIPT_CONFIRMED",
        from_status=previous,
        to_status=indent.status,
    )
    return receipt


@transaction.atomic
def create_discrepancy_case(*, actor, receipt_id, description, evidence=None):
    if not actor.has_permission("purchase_stores.discrepancy.manage") and not actor.has_permission(
        "purchase_stores.indent.create"
    ):
        raise PermissionDeniedError(
            "This action requires a PSM employee or discrepancy permission."
        )
    receipt = (
        GoodsReceipt.objects.select_for_update()
        .select_related("purchase_order__indent")
        .filter(pk=receipt_id)
        .first()
    )
    if receipt is None:
        raise NotFoundError("No goods receipt was found.")
    indent = Indent.objects.select_for_update().get(pk=receipt.purchase_order.indent_id)
    if indent.requestor_user_id != actor.user_id and not _has_department_access(
        actor, indent.department_id
    ):
        raise PermissionDeniedError("You are not assigned to report discrepancies for this indent.")
    previous = indent.status
    if previous in {
        Indent.Status.RECEIPT_CONFIRMED,
        Indent.Status.GRN_ACCEPTED,
        Indent.Status.GRN_PARTIAL,
    }:
        validate_transition(previous, Indent.Status.DISCREPANCY_IDENTIFIED)
        indent.status = Indent.Status.DISCREPANCY_IDENTIFIED
        indent.save(update_fields=["status", "updated_at"])
        WorkflowAction.objects.create(
            indent=indent,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            action="DISCREPANCY_IDENTIFIED",
            from_status=previous,
            to_status=indent.status,
        )
    case = DiscrepancyCase.objects.create(
        goods_receipt=receipt,
        description=description,
        evidence=evidence or [],
    )
    if indent.status != Indent.Status.DISCREPANCY_CASE_OPEN:
        previous = indent.status
        validate_transition(previous, Indent.Status.DISCREPANCY_CASE_OPEN)
        indent.status = Indent.Status.DISCREPANCY_CASE_OPEN
        indent.save(update_fields=["status", "updated_at"])
        WorkflowAction.objects.create(
            indent=indent,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            action="DISCREPANCY_CASE_OPENED",
            from_status=previous,
            to_status=indent.status,
            details={"case_id": case.pk},
        )
    return case


@transaction.atomic
def resolve_discrepancy(*, actor, case_id, resolution_type, note="", communication=""):
    _require(actor, "purchase_stores.discrepancy.manage")
    case = (
        DiscrepancyCase.objects.select_for_update()
        .select_related("goods_receipt__purchase_order__indent")
        .filter(pk=case_id)
        .first()
    )
    if case is None:
        raise NotFoundError("No discrepancy case was found.")
    indent = case.goods_receipt.purchase_order.indent
    if not _has_department_access(actor, indent.department_id):
        raise PermissionDeniedError("You are not assigned to resolve cases for this department.")
    if case.status == DiscrepancyCase.Status.RESOLVED:
        raise ConflictError("This discrepancy case is already resolved.")
    receipt = case.goods_receipt
    if receipt.confirmed_at is not None and resolution_type in {"return", "replacement"}:
        for line in receipt.accepted_lines:
            stock = (
                StockBalance.objects.select_for_update()
                .filter(sku=_stock_sku(line), department_id=indent.department_id, is_central=False)
                .first()
            )
            quantity = Decimal(str(line.get("quantity", "0")))
            if stock is None or stock.quantity_on_hand - stock.quantity_reserved < quantity:
                raise ConflictError(
                    "The returned quantity is no longer available in stock for adjustment."
                )
            stock.quantity_on_hand -= quantity
            stock.save(update_fields=["quantity_on_hand", "updated_at"])
            StockLedgerEntry.objects.create(
                stock=stock,
                kind=StockLedgerEntry.Kind.ADJUSTMENT,
                quantity_delta=-quantity,
                reference=receipt.receipt_reference,
                actor_user_id=actor.user_id,
                note="Discrepancy return or replacement adjustment",
            )
    if communication:
        case.vendor_communications = [
            *case.vendor_communications,
            {"at": timezone.now().isoformat(), "by": actor.user_id, "message": communication},
        ]
    if resolution_type == "replacement":
        if case.replacement_traversal_count >= 1:
            raise ConflictError(
                "Only one replacement traversal is permitted for a discrepancy case."
            )
        case.replacement_traversal_count += 1
        case.status = DiscrepancyCase.Status.REPLACEMENT
        indent = case.goods_receipt.purchase_order.indent
        indent.status = Indent.Status.REPLACEMENT_AWAITED
        indent.save(update_fields=["status", "updated_at"])
    elif resolution_type == "return":
        case.status = DiscrepancyCase.Status.RETURN
        case.resolution = note
        case.status = DiscrepancyCase.Status.RESOLVED
        case.resolved_at = timezone.now()
        if receipt.confirmed_at is not None:
            indent.status = Indent.Status.RECEIPT_CONFIRMED
            indent.save(update_fields=["status", "updated_at"])
    elif resolution_type == "warranty":
        case.status = DiscrepancyCase.Status.WARRANTY
        case.resolution = note
    elif resolution_type == "resolved":
        case.status = DiscrepancyCase.Status.RESOLVED
        case.resolution = note
        case.resolved_at = timezone.now()
    else:
        raise ConflictError("Resolution type must be replacement, return, warranty, or resolved.")
    case.save(
        update_fields=[
            "status",
            "resolution",
            "resolved_at",
            "replacement_traversal_count",
            "vendor_communications",
            "updated_at",
        ]
    )
    WorkflowAction.objects.create(
        indent=case.goods_receipt.purchase_order.indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="DISCREPANCY_RESOLVED"
        if case.status == DiscrepancyCase.Status.RESOLVED
        else "DISCREPANCY_UPDATED",
        reason=note,
        details={"case_id": case.pk, "resolution_type": resolution_type},
    )
    return case


@transaction.atomic
def verify_invoice(
    *,
    actor,
    purchase_order_id,
    invoice_number,
    invoice_amount,
    goods_receipt_id,
    match_details=None,
):
    _require(actor, "purchase_stores.invoice.manage")
    order = PurchaseOrder.objects.select_for_update().filter(pk=purchase_order_id).first()
    receipt = GoodsReceipt.objects.filter(
        pk=goods_receipt_id, purchase_order_id=purchase_order_id, confirmed_at__isnull=False
    ).first()
    if order is None or receipt is None:
        raise ConflictError("Invoice verification requires a linked, confirmed PO and GRN.")
    if order.vendor.status != Vendor.Status.VERIFIED:
        raise ConflictError(
            "Invoices for unverified vendors cannot be verified.", code="vendor_not_verified"
        )
    invoice = VendorInvoice.objects.create(
        purchase_order=order,
        goods_receipt=receipt,
        vendor=order.vendor,
        invoice_number=invoice_number,
        invoice_amount=invoice_amount,
        match_details=match_details or {},
    )
    po_lines = {_item_key(line): line for line in order.line_items}
    accepted_value = Decimal("0")
    quantity_match = bool(receipt.accepted_lines) and bool(po_lines)
    for line in receipt.accepted_lines:
        po_line = po_lines.get(_item_key(line))
        if po_line is None:
            quantity_match = False
            break
        received_quantity = Decimal(str(line.get("quantity", "0")))
        po_quantity = Decimal(str(po_line["quantity"]))
        if received_quantity <= 0 or received_quantity > po_quantity:
            quantity_match = False
            break
        accepted_value += received_quantity * Decimal(str(po_line["estimated_unit_cost"]))
    matched = (
        quantity_match
        and Decimal(invoice_amount) <= order.total_amount
        and Decimal(invoice_amount) <= accepted_value
        and not receipt.discrepancies.exclude(status=DiscrepancyCase.Status.RESOLVED).exists()
    )
    if not matched:
        invoice.status = VendorInvoice.Status.ON_HOLD
        invoice.hold_reason = (
            "Invoice amount or receipt discrepancy does not match the PO and accepted GRN."
        )
        invoice.save(update_fields=["status", "hold_reason", "updated_at"])
        return invoice
    invoice.status = VendorInvoice.Status.VERIFIED
    invoice.verified_by_user_id = actor.user_id
    invoice.verified_at = timezone.now()
    invoice.save(update_fields=["status", "verified_by_user_id", "verified_at", "updated_at"])
    indent = order.indent
    indent.status = Indent.Status.INVOICE_VERIFIED
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="INVOICE_VERIFIED",
        from_status=Indent.Status.RECEIPT_CONFIRMED,
        to_status=indent.status,
    )
    return invoice


@transaction.atomic
def process_payment(*, actor, invoice_id, amount, reference=""):
    _require(actor, "purchase_stores.invoice.manage")
    invoice = VendorInvoice.objects.select_for_update().filter(pk=invoice_id).first()
    if invoice is None:
        raise NotFoundError("No invoice was found.")
    if invoice.status not in {VendorInvoice.Status.VERIFIED, VendorInvoice.Status.PARTIALLY_PAID}:
        raise ConflictError("Only verified invoices can be paid.")
    if invoice.vendor.status != Vendor.Status.VERIFIED:
        raise ConflictError(
            "Payments for unverified vendors cannot be released.", code="vendor_not_verified"
        )
    paid = invoice.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    amount = Decimal(amount)
    if amount <= 0 or paid + amount > invoice.invoice_amount:
        raise ConflictError("Payment amount exceeds the verified invoice balance.")
    payment = VendorPayment.objects.create(
        invoice=invoice, amount=amount, reference=reference, processed_by_user_id=actor.user_id
    )
    paid += amount
    invoice.status = (
        VendorInvoice.Status.PAID
        if paid == invoice.invoice_amount
        else VendorInvoice.Status.PARTIALLY_PAID
    )
    invoice.save(update_fields=["status", "updated_at"])
    indent = invoice.purchase_order.indent
    indent.status = (
        Indent.Status.PAID
        if invoice.status == VendorInvoice.Status.PAID
        else Indent.Status.PARTIALLY_PAID
    )
    indent.save(update_fields=["status", "updated_at"])
    WorkflowAction.objects.create(
        indent=indent,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="PAYMENT_PROCESSED",
        from_status=Indent.Status.INVOICE_VERIFIED,
        to_status=indent.status,
        details={"amount": str(amount), "payment_id": payment.pk},
    )
    return payment


@transaction.atomic
def create_stock_transfer(*, actor, source_department_id, destination_department_id, lines):
    _require(actor, "purchase_stores.stock.manage")
    if source_department_id == destination_department_id:
        raise ConflictError("Stock transfer source and destination must differ.")
    if not DepartmentAccess.objects.filter(
        user_id=actor.user_id, department_id=destination_department_id, is_active=True
    ).exists() and not actor.has_permission("purchase_stores.policy.manage"):
        raise PermissionDeniedError("You are not assigned to the destination department.")
    transfer = StockTransfer.objects.create(
        reference=_reference("TR"),
        source_department_id=source_department_id,
        destination_department_id=destination_department_id,
        requested_by_user_id=actor.user_id,
        lines=lines,
    )
    for line in lines:
        balance = (
            StockBalance.objects.select_for_update()
            .filter(sku=line["sku"], department_id=source_department_id, is_central=False)
            .first()
        )
        quantity = Decimal(str(line["quantity"]))
        if balance is None or balance.quantity_available < quantity:
            raise ConflictError("The source department has insufficient unreserved stock.")
        balance.quantity_reserved += quantity
        balance.save(update_fields=["quantity_reserved", "updated_at"])
        StockTransferReservation.objects.create(transfer=transfer, stock=balance, quantity=quantity)
    return transfer


@transaction.atomic
def dispatch_stock_transfer(*, actor, transfer_id):
    _require(actor, "purchase_stores.stock.manage")
    transfer = (
        StockTransfer.objects.select_for_update()
        .filter(pk=transfer_id, status=StockTransfer.Status.REQUESTED)
        .first()
    )
    if transfer is None:
        raise NotFoundError("No pending stock transfer was found.")
    if not DepartmentAccess.objects.filter(
        user_id=actor.user_id, department_id=transfer.source_department_id, is_active=True
    ).exists() and not actor.has_permission("purchase_stores.policy.manage"):
        raise PermissionDeniedError("You are not assigned to the source department.")
    reservations = list(
        StockTransferReservation.objects.select_for_update()
        .filter(transfer=transfer, status=StockTransferReservation.Status.RESERVED)
        .select_related("stock")
    )
    if not reservations:
        raise ConflictError("The transfer has no active stock reservations.")
    for reservation in reservations:
        balance = reservation.stock
        quantity = reservation.quantity
        if balance.quantity_on_hand < quantity or balance.quantity_reserved < quantity:
            raise ConflictError("Reserved stock changed before dispatch.")
        balance.quantity_on_hand -= quantity
        balance.quantity_reserved -= quantity
        balance.save(update_fields=["quantity_on_hand", "quantity_reserved", "updated_at"])
        reservation.status = StockTransferReservation.Status.CONSUMED
        reservation.save(update_fields=["status", "updated_at"])
        item_name = next(
            (line.get("item_name", "") for line in transfer.lines if line["sku"] == balance.sku),
            "",
        )
        StockLedgerEntry.objects.create(
            stock=balance,
            kind=StockLedgerEntry.Kind.TRANSFER_OUT,
            quantity_delta=-quantity,
            reference=transfer.reference,
            actor_user_id=actor.user_id,
            note=item_name,
        )
    transfer.status = StockTransfer.Status.DISPATCHED
    transfer.dispatched_at = timezone.now()
    transfer.save(update_fields=["status", "dispatched_at", "updated_at"])
    return transfer


@transaction.atomic
def receive_stock_transfer(*, actor, transfer_id):
    _require(actor, "purchase_stores.stock.manage")
    transfer = (
        StockTransfer.objects.select_for_update()
        .filter(pk=transfer_id, status=StockTransfer.Status.DISPATCHED)
        .first()
    )
    if transfer is None:
        raise NotFoundError("No dispatched stock transfer was found.")
    if not DepartmentAccess.objects.filter(
        user_id=actor.user_id, department_id=transfer.destination_department_id, is_active=True
    ).exists() and not actor.has_permission("purchase_stores.policy.manage"):
        raise PermissionDeniedError("You are not assigned to the destination department.")
    for line in transfer.lines:
        quantity = Decimal(str(line["quantity"]))
        balance, _ = StockBalance.objects.select_for_update().get_or_create(
            sku=line["sku"],
            department_id=transfer.destination_department_id,
            is_central=False,
            defaults={"item_name": line.get("item_name", line["sku"])},
        )
        balance.quantity_on_hand += quantity
        balance.save(update_fields=["quantity_on_hand", "updated_at"])
        StockLedgerEntry.objects.create(
            stock=balance,
            kind=StockLedgerEntry.Kind.TRANSFER_IN,
            quantity_delta=quantity,
            reference=transfer.reference,
            actor_user_id=actor.user_id,
            note=line.get("item_name", ""),
        )
    transfer.status = StockTransfer.Status.COMPLETED
    transfer.received_at = timezone.now()
    transfer.save(update_fields=["status", "received_at", "updated_at"])
    return transfer


def policy_value(key, default=None):
    row = PolicySetting.objects.filter(key=key).first()
    return default if row is None else row.value


@transaction.atomic
def set_policy_value(*, actor, key, value, description=""):
    _require(actor, "purchase_stores.policy.manage")
    if key in {"final_approval_threshold", "procurement_method_threshold"}:
        try:
            value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ConflictError(
                "Configured thresholds must be valid monetary amounts.", code="invalid_policy_value"
            ) from exc
        if value <= 0:
            raise ConflictError(
                "Configured thresholds must be greater than zero.", code="invalid_policy_value"
            )
        value = str(value)
    setting, _ = PolicySetting.objects.update_or_create(
        key=key,
        defaults={"value": value, "description": description, "updated_by_user_id": actor.user_id},
    )
    WorkflowAction.objects.create(
        indent=None,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="POLICY_UPDATED",
        details={"key": key, "value": value},
    )
    return setting


@transaction.atomic
def grant_department_access(*, actor, user_id, department_id):
    _require(actor, "purchase_stores.policy.manage")
    access, _ = DepartmentAccess.objects.update_or_create(
        user_id=user_id,
        department_id=department_id,
        defaults={"assigned_by_user_id": actor.user_id, "is_active": True},
    )
    WorkflowAction.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="DEPARTMENT_ACCESS_GRANTED",
        details={"user_id": user_id, "department_id": department_id},
    )
    return access


@transaction.atomic
def revoke_department_access(*, actor, user_id, department_id):
    _require(actor, "purchase_stores.policy.manage")
    access = (
        DepartmentAccess.objects.select_for_update()
        .filter(user_id=user_id, department_id=department_id, is_active=True)
        .first()
    )
    if access is None:
        raise NotFoundError("No active department assignment was found.")
    access.is_active = False
    access.save(update_fields=["is_active", "updated_at"])
    WorkflowAction.objects.create(
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="DEPARTMENT_ACCESS_REVOKED",
        details={"user_id": user_id, "department_id": department_id},
    )
    return access
