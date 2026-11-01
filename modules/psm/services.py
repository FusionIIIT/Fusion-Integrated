import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm import models as m
from modules.psm import selectors
from modules.psm.access import member, require
from modules.psm.domain.rules import TERMINAL, approval_route, decimal_value, procurement_method


def fail(condition, message):
    if not condition:
        raise ConflictError(message)


def text(data, key):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DomainError(f"{key} is required.")
    limit = {
        "item": 160,
        "name": 160,
        "gst": 32,
        "number": 100,
        "reference": 100,
        "location": 100,
        "destination": 100,
        "kind": 24,
    }.get(key, 20000)
    if len(value.strip()) > limit:
        raise DomainError(f"{key} is too long (maximum {limit} characters).")
    return value.strip()


def number(data, key, minimum=None):
    try:
        value = decimal_value(data.get(key))
    except ValueError as exc:
        raise DomainError(f"{key}: {exc}") from exc
    if minimum is not None and value < minimum:
        raise DomainError(f"{key} must be at least {minimum}.")
    precision = 2 if key in ("estimated_cost", "amount", "accounting_delta") else 3
    if abs(value) >= Decimal("10000000000000") or value.as_tuple().exponent < -precision:
        raise DomainError(f"{key} exceeds supported precision.")
    return value


def moment(data, key):
    from django.utils.dateparse import parse_datetime

    try:
        result = parse_datetime(text(data, key))
    except ValueError as exc:
        raise DomainError(f"{key} must be an ISO date and time.") from exc
    if result is None:
        raise DomainError(f"{key} must be an ISO date and time.")
    return timezone.make_aware(result) if timezone.is_naive(result) else result


def data_list(data, key):
    result = data.get(key)
    if not isinstance(result, list) or not result:
        raise DomainError(f"{key} must be a nonempty list.")
    return result


def active_policy():
    policy = m.Policy.objects.filter(active=True).first()
    if policy is None:
        raise ConflictError("Procurement policy is not configured. Ask the P&S administrator.")
    return policy.configuration


def audit(principal, obj, action, snapshot=None, department=None):
    scope = member(principal)
    m.Audit.objects.create(
        actor_id=principal.user_id,
        department=department or getattr(obj, "department", scope.department),
        entity=obj._meta.model_name,
        object_id=obj.pk,
        action=action,
        snapshot=snapshot or {},
    )


def notify(indent, event, message):
    recipients = {indent.requestor_id}
    recipients.update(
        m.Membership.objects.filter(
            role__in=["ps_admin", "accounts", "final_authority"]
        ).values_list("user_id", flat=True)
    )
    recipients.update(
        m.Membership.objects.filter(
            department=indent.department, role__in=["department_admin", "department_head"]
        ).values_list("user_id", flat=True)
    )
    for user_id in recipients:
        m.Notification.objects.create(
            user_id=user_id,
            indent=indent,
            event=event,
            message=message,
            deduplication_key=str(uuid.uuid4()),
        )


def save_indent(principal, obj, action, details=None):
    obj.save()
    audit(
        principal,
        obj,
        action,
        {
            "status": obj.status,
            "version": obj.version,
            "item": obj.item,
            "quantity": str(obj.quantity),
            "estimated_cost": str(obj.estimated_cost),
            "justification": obj.justification,
            **(details or {}),
        },
    )
    notify(obj, action, f"{obj.item}: {action.replace('_', ' ')} ({obj.status.replace('_', ' ')}).")
    return obj


def _policy_configuration(config):
    if not isinstance(config, dict):
        raise TypeError("configuration must be an object.")
    required = (
        "approval_bands",
        "tender_threshold",
        "duplicate_fields",
        "sla_reminder_hours",
        "sla_escalation_hours",
        "modify_states",
        "withdraw_states",
        "cancel_states",
    )
    if any(key not in config for key in required):
        raise ValueError(
            "Specify approval, tender, duplicate, SLA and lifecycle policy parameters."
        )
    for key in ("modify_states", "withdraw_states", "cancel_states", "duplicate_fields"):
        if not isinstance(config[key], list) or any(not isinstance(x, str) for x in config[key]):
            raise ValueError(f"{key} must be a list of strings.")
    fields = {"item", "quantity", "estimated_cost", "department", "requestor_id", "justification"}
    if not config["duplicate_fields"] or not set(config["duplicate_fields"]) <= fields:
        raise ValueError("Configure supported duplicate comparison fields.")
    bands = config["approval_bands"]
    if not isinstance(bands, list) or not bands or bands[-1].get("up_to") is not None:
        raise ValueError("Approval bands must end in an unbounded band.")
    previous = None
    for i, band in enumerate(bands):
        ceiling = band.get("up_to")
        if ceiling is None and i != len(bands) - 1:
            raise ValueError("Only the last approval band may be unbounded.")
        if ceiling is not None:
            amount = decimal_value(ceiling)
            if previous is not None and amount <= previous:
                raise ValueError("Approval bands must be ordered by increasing value.")
            previous = amount
    routes = [b["roles"] for b in bands] + list(config.get("priority_routes", {}).values())
    for route in routes:
        if (
            not route
            or route[0] != "department_admin"
            or "ps_admin" not in route
            or len(set(route)) != len(route)
            or any(
                role not in ("department_admin", "department_head", "ps_admin", "final_authority")
                for role in route
            )
        ):
            raise ValueError("Invalid approval route.")
        if "final_authority" in route and route[-1] != "final_authority":
            raise ValueError("Final authority must follow the P&S recommendation.")
    procurement_method(config, Decimal("0"))
    for key in ("sla_reminder_hours", "sla_escalation_hours"):
        if decimal_value(config[key]) <= 0:
            raise ValueError("SLA intervals must be positive.")
    for key in ("minimum_quantity", "minimum_estimated_cost", "duplicate_window_hours"):
        if key in config:
            decimal_value(config[key])
    return config


def policy_validate(config):
    try:
        _policy_configuration(config)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        raise DomainError(f"Invalid policy: {exc}") from exc


def validate_indent_policy(obj):
    for field, key in (
        ("quantity", "minimum_quantity"),
        ("estimated_cost", "minimum_estimated_cost"),
    ):
        bound = obj.policy_snapshot.get(key)
        if bound is not None and getattr(obj, field) < decimal_value(bound):
            raise DomainError(f"{field} is below the configured policy minimum.")


def vendor_version(principal, obj):
    m.VendorVersion.objects.create(
        vendor=obj,
        version=obj.version,
        actor_id=principal.user_id,
        snapshot={
            "name": obj.name,
            "gst": obj.gst,
            "bank_details": obj.bank_details,
            "compliance": obj.compliance,
            "verified": obj.verified,
        },
    )


def stock_snapshot(obj):
    rows = m.Stock.objects.filter(item=obj.item, location__in=[obj.department, "CENTRAL"])
    return [
        {"stock_id": str(s.pk), "location": s.location, "available": str(s.quantity - s.reserved)}
        for s in rows
    ]


def duplicates(obj):
    fields = obj.policy_snapshot.get("duplicate_fields", [])
    if not fields:
        return []
    qs = (
        m.Indent.objects.exclude(pk=obj.pk)
        .exclude(status__in=TERMINAL)
        .filter(**{f: getattr(obj, f) for f in fields})
    )
    window = obj.policy_snapshot.get("duplicate_window_hours")
    if window is not None:
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(hours=float(window)))
    return list(map(str, qs.values_list("pk", flat=True)[:50]))


def release_reservations(obj):
    for reservation in obj.reservations.select_for_update().order_by("stock_id"):
        stock = m.Stock.objects.select_for_update().get(pk=reservation.stock_id)
        stock.reserved -= reservation.remaining
        stock.save()
        reservation.remaining = 0
        reservation.save()


def reserve(principal, obj):
    require(principal, ["department_admin", "ps_admin"], obj.department)
    fail(obj.status in ("submitted", "modified"), "Stock check is not available in this state.")
    fail(obj.quantity > 0, "Stock allocation needs a quantity greater than zero.")
    stocks = list(
        m.Stock.objects.select_for_update()
        .filter(item=obj.item, location__in=[obj.department, "CENTRAL"])
        .order_by("id")
    )
    obj.stock_result = stock_snapshot(obj)
    if sum((s.quantity - s.reserved for s in stocks), Decimal("0")) >= obj.quantity:
        remaining = obj.quantity
        for stock in stocks:
            qty = min(remaining, stock.quantity - stock.reserved)
            if qty > 0:
                m.Reservation.objects.create(indent=obj, stock=stock, quantity=qty, remaining=qty)
                stock.reserved += qty
                stock.save()
                remaining -= qty
        obj.status = "stock_reserved"
    else:
        obj.status = "external_required"
    return save_indent(principal, obj, "stock_checked")


def post_receipt(principal, obj, receipt):
    fail(not receipt.posted, "This receipt is already posted.")
    if obj.method == "internal":
        remaining = receipt.accepted
        for res in obj.reservations.select_for_update().order_by("stock_id"):
            qty = min(remaining, res.remaining)
            if qty:
                stock = m.Stock.objects.select_for_update().get(pk=res.stock_id)
                stock.quantity -= qty
                stock.reserved -= qty
                stock.save()
                res.remaining -= qty
                res.save()
                m.LedgerEntry.objects.create(
                    stock=stock,
                    delta=-qty,
                    source=str(receipt.pk),
                    reason="Confirmed internal issue",
                    actor_id=principal.user_id,
                )
                remaining -= qty
        fail(remaining == 0, "Receipt exceeds reserved stock.")
    elif receipt.accepted > 0:
        stock, _ = m.Stock.objects.get_or_create(item=obj.item, location=obj.department)
        stock = m.Stock.objects.select_for_update().get(pk=stock.pk)
        stock.quantity += receipt.accepted
        stock.save()
        m.LedgerEntry.objects.create(
            stock=stock,
            delta=receipt.accepted,
            source=str(receipt.pk),
            reason="Confirmed goods receipt",
            actor_id=principal.user_id,
        )
    receipt.posted = True
    receipt.save()


@transaction.atomic
def create_indent(principal, data):
    scope = require(principal, ["employee", "department_admin", "department_head", "ps_admin"])
    obj = m.Indent.objects.create(
        requestor_id=principal.user_id,
        department=scope.department,
        item=text(data, "item"),
        quantity=number(data, "quantity"),
        estimated_cost=number(data, "estimated_cost"),
        justification=text(data, "justification"),
    )
    return save_indent(principal, obj, "draft_created")


@transaction.atomic
def indent_action(principal, pk, action, data):
    obj = selectors.indent(principal, pk, lock=True)
    scope = member(principal)
    if action in ("submit", "modify", "withdraw", "cancel", "repeat", "confirm_receipt"):
        fail(obj.requestor_id == principal.user_id, "Only the requestor may perform this action.")
        require(principal, ["employee", "department_admin", "department_head", "ps_admin"])
    if action == "submit":
        fail(obj.status == "draft", "Only drafts can be submitted.")
        obj.policy_snapshot = active_policy()
        try:
            obj.approval_route = approval_route(
                obj.policy_snapshot, obj.estimated_cost, obj.priority
            )
        except ValueError as exc:
            raise DomainError(str(exc)) from exc
        validate_indent_policy(obj)
        obj.duplicate_ids = duplicates(obj)
        obj.stock_result = stock_snapshot(obj)
        obj.submitted_at = timezone.now()
        obj.status = "submitted"
    elif action == "reserve":
        return reserve(principal, obj)
    elif action in ("withdraw", "cancel", "modify"):
        allowed = obj.policy_snapshot.get(action + "_states", [])
        fail(obj.status in allowed, "Current policy does not permit this action in this state.")
        fail(
            not m.PurchaseOrder.objects.filter(indent=obj).exists() and obj.dispatch_at is None,
            "An issued order or dispatched goods must use the receipt and resolution workflow.",
        )
        release_reservations(obj)
        if action == "modify":
            for field in ("item", "justification"):
                setattr(obj, field, text(data, field))
            obj.quantity = number(data, "quantity")
            obj.estimated_cost = number(data, "estimated_cost")
            validate_indent_policy(obj)
            obj.version += 1
            obj.status = "modified"
            obj.approval_step = 0
            obj.method = ""
            obj.duplicate_review = ""
            obj.approval_route = approval_route(
                obj.policy_snapshot, obj.estimated_cost, obj.priority
            )
            obj.duplicate_ids = duplicates(obj)
        else:
            obj.status = "withdrawn" if action == "withdraw" else "cancelled"
    elif action == "repeat":
        return create_indent(
            principal,
            {
                "item": obj.item,
                "quantity": str(obj.quantity),
                "estimated_cost": str(obj.estimated_cost),
                "justification": obj.justification,
            },
        )
    elif action == "review":
        fail(
            obj.status in ("stock_reserved", "external_required", "awaiting_approval"),
            "Stock must be checked before review.",
        )
        fail(obj.approval_step < len(obj.approval_route), "All reviews have already completed.")
        expected = obj.approval_route[obj.approval_step]
        require(principal, [expected], obj.department)
        decision = text(data, "decision")
        fail(decision in ("approve", "reject", "changes"), "Choose approve, reject or changes.")
        reason = data.get("reason", "").strip()
        if decision == "reject":
            fail(bool(reason), "Rejection requires a justification.")
            release_reservations(obj)
            obj.status = "rejected"
        elif decision == "changes":
            fail(
                scope.role == "department_head" and bool(reason),
                "Only the department head may recommend changes, with a reason.",
            )
            obj.status = "changes_requested"
        else:
            if expected == "department_admin":
                fail(
                    not obj.duplicate_ids or bool(data.get("duplicate_review", "").strip()),
                    "Review the potential duplicate before approving.",
                )
                obj.duplicate_review = data.get("duplicate_review", "")
                try:
                    obj.priority = int(data.get("priority", 0))
                except (ValueError, TypeError) as exc:
                    raise DomainError("priority must be an integer.") from exc
                obj.approval_route = approval_route(
                    obj.policy_snapshot, obj.estimated_cost, obj.priority
                )
                if obj.status == "stock_reserved":
                    obj.method = "internal"
                    obj.approval_step = len(obj.approval_route)
                    obj.status = "internal_approved"
                    return save_indent(principal, obj, "internal_approved", {"reason": reason})
            if expected == "ps_admin":
                obj.method = procurement_method(obj.policy_snapshot, obj.estimated_cost)
            obj.approval_step += 1
            obj.status = (
                "authorized"
                if obj.approval_step == len(obj.approval_route)
                else "awaiting_approval"
            )
        return save_indent(principal, obj, decision, {"reason": reason, "role": expected})
    elif action == "dispatch":
        require(principal, ["department_admin", "ps_admin"], obj.department)
        fail(obj.status == "internal_approved", "An approved internal issue is required.")
        obj.pick_at = moment(data, "pick_at")
        obj.dispatch_at = moment(data, "dispatch_at")
        fail(obj.dispatch_at >= obj.pick_at, "Dispatch cannot precede picking.")
        obj.status = "dispatched"
    elif action == "confirm_receipt":
        receipt = obj.receipts.select_for_update().filter(pk=data.get("receipt_id")).first()
        fail(receipt is not None and receipt.confirmed_at is None, "Choose an unconfirmed receipt.")
        fail(
            not obj.cases.exclude(status="resolved").exists(),
            "Resolve all discrepancies before confirmation.",
        )
        fail(receipt.accepted > 0, "There are no accepted quantities to confirm.")
        receipt.confirmed_at = timezone.now()
        post_receipt(principal, obj, receipt)
        accepted = obj.receipts.filter(posted=True).aggregate(n=Sum("accepted"))["n"] or 0
        obj.status = (
            ("completed" if obj.method == "internal" else "receipt_confirmed")
            if accepted >= obj.quantity
            else "partial_received"
        )
    else:
        raise DomainError("Unknown indent action.")
    return save_indent(principal, obj, action)


@transaction.atomic
def create_vendor(principal, data):
    require(principal, ["ps_admin"])
    obj = m.Vendor.objects.create(
        name=text(data, "name"),
        gst=text(data, "gst"),
        bank_details=text(data, "bank_details"),
        compliance=data_list(data, "compliance"),
    )
    vendor_version(principal, obj)
    audit(
        principal,
        obj,
        "created",
        {"version": obj.version, "name": obj.name, "gst": obj.gst, "compliance": obj.compliance},
    )
    return obj


@transaction.atomic
def vendor_action(principal, pk, action, data):
    require(principal, ["ps_admin"])
    obj = m.Vendor.objects.select_for_update().filter(pk=pk).first()
    if obj is None:
        raise NotFoundError()
    if action == "verify":
        fail(
            bool(obj.gst and obj.bank_details and obj.compliance),
            "GST, bank and compliance data are required.",
        )
        obj.verified = True
    elif action == "update":
        for field in ("name", "gst", "bank_details"):
            setattr(obj, field, text(data, field))
        obj.compliance = data_list(data, "compliance")
        obj.version += 1
        obj.verified = False
    else:
        raise DomainError("Unknown vendor action.")
    obj.save()
    vendor_version(principal, obj)
    audit(
        principal,
        obj,
        action,
        {
            "version": obj.version,
            "name": obj.name,
            "gst": obj.gst,
            "compliance": obj.compliance,
            "verified": obj.verified,
        },
    )
    return obj


@transaction.atomic
def create_tender(principal, data):
    require(principal, ["ps_admin"])
    obj = selectors.indent(principal, data.get("indent"), lock=True)
    fail(obj.status == "authorized" and obj.method == "tender", "Tender authorization is required.")
    criteria = data_list(data, "criteria")
    fail(all(isinstance(c, str) and c.strip() for c in criteria), "Criteria must be named strings.")
    tender = m.Tender.objects.create(
        indent=obj, criteria=criteria, closes_at=moment(data, "closes_at")
    )
    fail(tender.closes_at > timezone.now(), "Tender close date must be in the future.")
    obj.status = "tender_published"
    save_indent(principal, obj, "tender_published")
    return tender


@transaction.atomic
def create_bid(principal, data):
    scope = require(principal, ["vendor", "ps_admin"])
    tender = m.Tender.objects.select_for_update().filter(pk=data.get("tender")).first()
    fail(
        tender is not None and tender.status == "published" and tender.closes_at > timezone.now(),
        "This tender is not accepting bids.",
    )
    vendor_id = scope.vendor_id if scope.role == "vendor" else data.get("vendor")
    vendor = m.Vendor.objects.filter(pk=vendor_id).first()
    fail(vendor is not None, "Vendor not found.")
    fail(not tender.bids.filter(vendor=vendor).exists(), "This vendor has already submitted a bid.")
    bid = m.Bid.objects.create(
        tender=tender,
        vendor=vendor,
        amount=number(data, "amount", 0),
        proposal=text(data, "proposal"),
    )
    audit(principal, bid, "bid_received")
    return bid


@transaction.atomic
def tender_action(principal, pk, action, data):
    tender = m.Tender.objects.select_for_update().filter(pk=pk).first()
    if tender is None:
        raise NotFoundError()
    require(principal, ["committee"])
    fail(tender.status != "selected", "Tender selection is already approved.")
    fail(timezone.now() >= tender.closes_at, "Bids remain sealed until the tender closes.")
    bid = tender.bids.select_for_update().filter(pk=data.get("bid")).first()
    fail(bid is not None, "Choose a bid belonging to this tender.")
    if action == "evaluate":
        evaluation = data.get("evaluation")
        fail(
            isinstance(evaluation, dict) and set(evaluation) == set(tender.criteria),
            "Record evaluation against every published criterion.",
        )
        bid.evaluation = evaluation
        bid.save()
        audit(principal, bid, "evaluated", evaluation)
    elif action == "select":
        fail(bool(bid.evaluation), "Evaluate the selected bid first.")
        tender.decision = text(data, "reason")
        tender.selected_bid_id = bid.pk
        tender.status = "selected"
        tender.save()
        obj = m.Indent.objects.select_for_update().get(pk=tender.indent_id)
        obj.status = "tender_selected"
        save_indent(
            principal, obj, "committee_selection", {"bid": str(bid.pk), "reason": tender.decision}
        )
    else:
        raise DomainError("Unknown tender action.")
    return tender


@transaction.atomic
def create_order(principal, data):
    require(principal, ["ps_admin"])
    obj = selectors.indent(principal, data.get("indent"), lock=True)
    fail(obj.status in ("authorized", "tender_selected"), "All approvals must complete first.")
    vendor = m.Vendor.objects.select_for_update().filter(pk=data.get("vendor")).first()
    fail(vendor is not None and vendor.verified, "A verified vendor is required.")
    amount = number(data, "amount", 0)
    fail(
        amount <= obj.estimated_cost,
        "Order value exceeds the approved estimate; modify and reapprove the indent.",
    )
    if obj.method == "tender":
        tender = m.Tender.objects.get(indent=obj)
        bid = tender.bids.filter(pk=tender.selected_bid_id).first()
        fail(
            tender.status == "selected"
            and bid is not None
            and bid.vendor_id == vendor.pk
            and bid.amount == amount,
            "PO must match the committee-approved bid.",
        )
    else:
        fail(obj.method == "direct", "Procurement method must be selected.")
    order = m.PurchaseOrder.objects.create(
        indent=obj,
        vendor=vendor,
        quantity=obj.quantity,
        amount=amount,
        planned_delivery=moment(data, "planned_delivery"),
    )
    obj.status = "po_issued"
    save_indent(principal, obj, "po_issued")
    return order


@transaction.atomic
def order_action(principal, pk, action, data):
    require(principal, ["ps_admin"])
    order = m.PurchaseOrder.objects.filter(pk=pk).first()
    if order is None:
        raise NotFoundError()
    obj = selectors.indent(principal, order.indent_id, lock=True)
    if action == "schedule":
        order.planned_delivery = moment(data, "planned_delivery")
    elif action == "deliver":
        fail(order.status == "issued", "Delivery is already recorded.")
        order.actual_delivery = moment(data, "actual_delivery")
        order.status = "delivered"
        obj.status = "delivered"
    else:
        raise DomainError("Unknown order action.")
    order.save()
    save_indent(principal, obj, action)
    return order


@transaction.atomic
def create_receipt(principal, data):
    obj = selectors.indent(principal, data.get("indent"), lock=True)
    scope = member(principal)
    if scope.role == "employee":
        fail(obj.requestor_id == principal.user_id, "Only the requestor may inspect this delivery.")
    require(principal, ["employee", "department_admin", "department_head"], obj.department)
    fail(
        obj.status
        in ("delivered", "dispatched", "partial_received", "replacement_awaited", "grn_recorded"),
        "Delivery must be recorded before inspection.",
    )
    accepted, rejected = number(data, "accepted", 0), number(data, "rejected", 0)
    fail(accepted + rejected > 0, "Record the inspected quantity.")
    prior = obj.receipts.aggregate(n=Sum("accepted"))["n"] or 0
    fail(prior + accepted <= obj.quantity, "Accepted quantity exceeds the order.")
    fail(
        accepted + rejected <= obj.quantity - prior, "Inspection exceeds the outstanding quantity."
    )
    case_id = data.get("replacement_case_id")
    if obj.status == "replacement_awaited":
        case = obj.cases.filter(pk=case_id, status="replacement_awaited").first()
        fail(case is not None, "A replacement inspection must reference its case.")
        fail(
            not obj.receipts.filter(replacement_case_id=case.pk).exists(),
            "One replacement traversal is already recorded; open a new case if needed.",
        )
        case.status = "resolved" if rejected == 0 else "open"
        case.save()
    receipt = m.Receipt.objects.create(
        indent=obj,
        accepted=accepted,
        rejected=rejected,
        inspected_by=principal.user_id,
        inspection=text(data, "inspection"),
        replacement_case_id=case_id,
    )
    if rejected:
        m.Discrepancy.objects.create(
            indent=obj,
            receipt=receipt,
            description=receipt.inspection,
            evidence=data.get("evidence", []),
            kind="rejection",
        )
        obj.status = "discrepancy"
    else:
        obj.status = "grn_recorded"
    save_indent(principal, obj, "grn_recorded")
    return receipt


@transaction.atomic
def create_case(principal, data):
    obj = selectors.indent(principal, data.get("indent"), lock=True)
    require(principal, ["employee", "department_admin", "department_head"], obj.department)
    fail(
        obj.status
        in (
            "delivered",
            "dispatched",
            "grn_recorded",
            "partial_received",
            "receipt_confirmed",
            "discrepancy",
            "completed",
            "paid",
            "partially_paid",
        ),
        "No delivery exists for this case.",
    )
    case = m.Discrepancy.objects.create(
        indent=obj,
        description=text(data, "description"),
        evidence=data_list(data, "evidence"),
        kind=text(data, "kind"),
    )
    obj.status = "discrepancy"
    save_indent(principal, obj, "discrepancy_opened")
    return case


@transaction.atomic
def case_action(principal, pk, action, data):
    case = selectors.collection(principal, "cases").filter(pk=pk).first()
    if case is None:
        raise NotFoundError()
    obj = selectors.indent(principal, case.indent_id, lock=True)
    case = m.Discrepancy.objects.select_for_update().get(pk=case.pk)
    if action == "communicate":
        require(principal, ["ps_admin", "vendor", "accounts"])
        m.Communication.objects.create(
            case=case, actor_id=principal.user_id, message=text(data, "message")
        )
        audit(principal, obj, "case_communication", {"case": str(case.pk)})
        return case
    require(principal, ["ps_admin"])
    fail(case.status == "open", "Case is already resolved or awaiting replacement.")
    case.resolution = text(data, "resolution")
    if action == "replace":
        case.status = "replacement_awaited"
        obj.status = "replacement_awaited"
    elif action == "resolve":
        case.inventory_delta = number(data, "inventory_delta")
        case.accounting_delta = number(data, "accounting_delta")
        fail(
            obj.policy_snapshot.get("resolution_adjustments") is True
            or (not case.inventory_delta and not case.accounting_delta),
            "Resolution adjustments require explicit policy authorization.",
        )
        fail(
            case.inventory_delta <= 0,
            "Record additional accepted goods through inspection and confirmation.",
        )
        confirmed = obj.receipts.filter(posted=True).aggregate(n=Sum("accepted"))["n"] or 0
        fail(
            -case.inventory_delta <= confirmed,
            "Return adjustment exceeds posted received quantity.",
        )
        if case.inventory_delta:
            stock = (
                m.Stock.objects.select_for_update()
                .filter(item=obj.item, location=obj.department)
                .first()
            )
            fail(stock is not None, "Stock record is required for an adjustment.")
            fail(
                stock.quantity + case.inventory_delta >= stock.reserved,
                "Adjustment would consume reserved stock.",
            )
            stock.quantity += case.inventory_delta
            stock.save()
            m.LedgerEntry.objects.create(
                stock=stock,
                delta=case.inventory_delta,
                source=str(case.pk),
                reason=case.resolution,
                actor_id=principal.user_id,
            )
        case.status = "resolved"
        obj.status = "grn_recorded"
    else:
        raise DomainError("Unknown case action.")
    case.save()
    save_indent(
        principal,
        obj,
        "case_" + action,
        {
            "case": str(case.pk),
            "resolution": case.resolution,
            "inventory_delta": str(case.inventory_delta),
            "accounting_delta": str(case.accounting_delta),
        },
    )
    return case


@transaction.atomic
def create_invoice(principal, data):
    require(principal, ["accounts"])
    po = m.PurchaseOrder.objects.filter(pk=data.get("po")).first()
    fail(po is not None, "Purchase order not found.")
    selectors.indent(principal, po.indent_id, lock=True)
    fail(
        not po.invoices.filter(number=data.get("number")).exists(),
        "Invoice number already exists for this PO.",
    )
    obj = m.Invoice.objects.create(
        po=po,
        number=text(data, "number"),
        quantity=number(data, "quantity", 0),
        amount=number(data, "amount", 0),
    )
    audit(principal, po.indent, "invoice_recorded", {"invoice": str(obj.pk)})
    notify(po.indent, "invoice", "Invoice recorded for verification.")
    return obj


def match_invoice(invoice):
    obj, po = invoice.po.indent, invoice.po
    accepted = obj.receipts.filter(posted=True, confirmed_at__isnull=False).aggregate(
        n=Sum("accepted")
    )["n"] or Decimal("0")
    fail(accepted > 0 and po.quantity > 0, "Confirmed accepted GRN is required.")
    fail(not obj.cases.exclude(status="resolved").exists(), "Unresolved discrepancy.")
    fail(po.vendor.verified, "Vendor must be verified.")
    invoices = po.invoices.exclude(pk=invoice.pk).filter(
        status__in=["verified", "partially_paid", "paid"]
    )
    accepted += obj.cases.filter(status="resolved", inventory_delta__lt=0).aggregate(
        n=Sum("inventory_delta")
    )["n"] or Decimal("0")
    prior_qty = invoices.aggregate(n=Sum("quantity"))["n"] or Decimal("0")
    prior_amount = invoices.aggregate(n=Sum("amount"))["n"] or Decimal("0")
    fail(
        invoice.quantity > 0 and invoice.quantity + prior_qty <= accepted,
        "Invoice exceeds confirmed accepted quantity.",
    )
    adjustments = obj.cases.filter(status="resolved").aggregate(n=Sum("accounting_delta"))[
        "n"
    ] or Decimal("0")
    expected = (po.amount * invoice.quantity / po.quantity).quantize(Decimal("0.01"))
    fail(
        invoice.amount == expected and prior_amount + invoice.amount <= po.amount + adjustments,
        "PO, GRN and invoice amounts do not match.",
    )
    if invoice.quantity != po.quantity:
        fail(
            obj.policy_snapshot.get("partial_payments") is True,
            "Partial-payment policy is not enabled.",
        )
    return obj


@transaction.atomic
def invoice_action(principal, pk, action, data):
    require(principal, ["accounts"])
    invoice = m.Invoice.objects.filter(pk=pk).select_related("po__indent", "po__vendor").first()
    if invoice is None:
        raise NotFoundError()
    obj = selectors.indent(principal, invoice.po.indent_id, lock=True)
    invoice = (
        m.Invoice.objects.select_for_update().select_related("po__indent", "po__vendor").get(pk=pk)
    )
    m.Vendor.objects.select_for_update().get(pk=invoice.po.vendor_id)
    if action == "verify":
        fail(
            invoice.status in ("pending", "held", "verified"), "Paid invoices cannot be reverified."
        )
        try:
            match_invoice(invoice)
            invoice.status, invoice.hold_reason = "verified", ""
        except ConflictError as exc:
            invoice.status, invoice.hold_reason = "held", str(exc)
    elif action == "hold":
        fail(invoice.status != "paid", "A paid invoice cannot be held.")
        invoice.status, invoice.hold_reason = "held", text(data, "reason")
    elif action == "pay":
        fail(invoice.status in ("verified", "partially_paid"), "Verify the invoice before payment.")
        match_invoice(invoice)
        amount = number(data, "amount", Decimal("0.01"))
        paid = invoice.payments.aggregate(n=Sum("amount"))["n"] or Decimal("0")
        fail(paid + amount <= invoice.amount, "Payment exceeds outstanding invoice amount.")
        if paid + amount != invoice.amount:
            fail(
                obj.policy_snapshot.get("partial_payments") is True,
                "Partial-payment policy is not enabled.",
            )
        reference = text(data, "reference")
        fail(
            not m.Payment.objects.filter(reference=reference).exists(),
            "This payment reference is already recorded.",
        )
        m.Payment.objects.create(invoice=invoice, amount=amount, reference=reference)
        invoice.status = "paid" if paid + amount == invoice.amount else "partially_paid"
        obj.status = "partially_paid"
        total = (
            m.Payment.objects.filter(invoice__po=invoice.po).aggregate(n=Sum("amount"))["n"] or 0
        )
        adjustments = (
            obj.cases.filter(status="resolved").aggregate(n=Sum("accounting_delta"))["n"] or 0
        )
        if total == invoice.po.amount + adjustments:
            obj.status = "paid"
    else:
        raise DomainError("Unknown invoice action.")
    invoice.save()
    save_indent(
        principal,
        obj,
        "invoice_" + action,
        {"invoice": str(invoice.pk), "status": invoice.status, "reason": invoice.hold_reason},
    )
    return invoice


@transaction.atomic
def create_transfer(principal, data):
    scope = require(principal, ["department_admin", "ps_admin"])
    source = m.Stock.objects.filter(pk=data.get("source")).first()
    fail(source is not None, "Source stock not found.")
    destination = (
        scope.department if scope.role == "department_admin" else text(data, "destination")
    )
    fail(source.location != destination, "Source and destination must differ.")
    fail(
        source.quantity - source.reserved >= number(data, "quantity", Decimal("0.001")),
        "Insufficient source availability for the requested transfer.",
    )
    obj = m.Transfer.objects.create(
        source=source,
        destination=destination,
        quantity=number(data, "quantity", Decimal("0.001")),
        requestor_id=principal.user_id,
        reason=text(data, "reason"),
    )
    audit(principal, obj, "transfer_requested", department=destination)
    notify_transfer(obj, "transfer_requested")
    return obj


@transaction.atomic
def transfer_action(principal, pk, action, data):
    obj = selectors.collection(principal, "transfers").select_for_update().filter(pk=pk).first()
    if obj is None:
        raise NotFoundError()
    if action == "dispatch":
        require(principal, ["department_admin", "ps_admin"], obj.source.location)
        fail(obj.status == "requested", "Transfer has already been processed.")
        stock = m.Stock.objects.select_for_update().get(pk=obj.source_id)
        fail(
            stock.quantity - stock.reserved >= obj.quantity, "Insufficient allocable source stock."
        )
        stock.reserved += obj.quantity
        stock.save()
        obj.status = "dispatched"
    elif action == "confirm":
        require(principal, ["department_admin", "ps_admin"], obj.destination)
        fail(obj.status == "dispatched", "Only dispatched transfers can be confirmed.")
        destination, _ = m.Stock.objects.get_or_create(
            item=obj.source.item, location=obj.destination
        )
        stocks = {
            s.pk: s
            for s in m.Stock.objects.select_for_update()
            .filter(pk__in=[obj.source_id, destination.pk])
            .order_by("id")
        }
        source, destination = stocks[obj.source_id], stocks[destination.pk]
        source.quantity -= obj.quantity
        source.reserved -= obj.quantity
        destination.quantity += obj.quantity
        source.save()
        destination.save()
        for stock, qty in [(source, -obj.quantity), (destination, obj.quantity)]:
            m.LedgerEntry.objects.create(
                stock=stock,
                delta=qty,
                source=str(obj.pk),
                reason=obj.reason,
                actor_id=principal.user_id,
            )
        obj.status = "completed"
    else:
        raise DomainError("Unknown transfer action.")
    obj.save()
    audit(principal, obj, "transfer_" + action, department=obj.destination)
    notify_transfer(obj, "transfer_" + action)
    return obj


@transaction.atomic
def configure_policy(principal, data):
    require(principal, ["ps_admin"])
    configuration = data.get("configuration")
    policy_validate(configuration)
    # Serialize activation against an existing membership, even on first configuration.
    m.Membership.objects.select_for_update().get(user_id=principal.user_id)
    m.Policy.objects.filter(active=True).update(active=False)
    obj = m.Policy.objects.create(name=text(data, "name"), configuration=configuration, active=True)
    audit(principal, obj, "policy_configured", configuration)
    return obj


@transaction.atomic
def adjust_stock(principal, data):
    scope = require(principal, ["department_admin", "ps_admin"])
    location = text(data, "location") if scope.role == "ps_admin" else scope.department
    reason, source = text(data, "reason"), text(data, "source")
    policy = active_policy()
    fail(
        policy.get("manual_adjustments") is True,
        "Manual corrections need explicit policy authorization.",
    )
    stock, _ = m.Stock.objects.get_or_create(item=text(data, "item"), location=location)
    stock = m.Stock.objects.select_for_update().get(pk=stock.pk)
    qty = number(data, "delta")
    fail(stock.quantity + qty >= stock.reserved, "Correction cannot consume reserved stock.")
    stock.quantity += qty
    stock.save()
    m.LedgerEntry.objects.create(
        stock=stock, delta=qty, source=source, reason=reason, actor_id=principal.user_id
    )
    audit(
        principal,
        stock,
        "stock_adjusted",
        {"delta": str(qty), "reason": reason, "source": source},
        department=location,
    )
    return stock


def notify_transfer(obj, event):
    users = m.Membership.objects.filter(
        role__in=["department_admin", "ps_admin"],
        department__in=[obj.source.location, obj.destination],
    ).values_list("user_id", flat=True)
    for uid in users:
        m.Notification.objects.create(
            user_id=uid,
            event=event,
            message=f"{obj.source.item}: {event.replace('_', ' ')} to {obj.destination}.",
            deduplication_key=f"transfer:{obj.pk}:{event}:{uid}",
        )
