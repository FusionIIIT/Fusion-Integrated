# Declarative transition tables for PSM aggregates (BW-PSM-01..08, BW-PSM-10, CW-PSM-01..02).
from __future__ import annotations

from dataclasses import dataclass, field

from modules.psm.domain.errors import ActorNotAllowedError, InvalidTransitionError

# Indent states
DRAFT = "draft"
SUBMITTED = "submitted"
STOCK_RESERVED = "stock_reserved"
INTERNAL_APPROVED = "internal_approved"
DISPATCHED = "dispatched"
GRN_RECORDED = "grn_recorded"
EXTERNAL_REQUIRED = "external_required"
DEPARTMENT_REVIEWED = "department_reviewed"
CHANGES_REQUESTED = "changes_requested"
HOD_RECOMMENDED = "hod_recommended"
AWAITING_FINAL_APPROVAL = "awaiting_final_approval"
PROCUREMENT_AUTHORIZED = "procurement_authorized"
TENDER_AWARDED = "tender_awarded"
PO_ISSUED = "po_issued"
FULFILLED = "fulfilled"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

INDENT_STATES = (
    DRAFT,
    SUBMITTED,
    STOCK_RESERVED,
    INTERNAL_APPROVED,
    DISPATCHED,
    GRN_RECORDED,
    EXTERNAL_REQUIRED,
    DEPARTMENT_REVIEWED,
    CHANGES_REQUESTED,
    HOD_RECOMMENDED,
    AWAITING_FINAL_APPROVAL,
    PROCUREMENT_AUTHORIZED,
    TENDER_AWARDED,
    PO_ISSUED,
    FULFILLED,
    REJECTED,
    WITHDRAWN,
)
INDENT_TERMINAL = frozenset({FULFILLED, REJECTED, WITHDRAWN})
INDENT_PENDING_APPROVAL = frozenset(
    {
        SUBMITTED,
        STOCK_RESERVED,
        EXTERNAL_REQUIRED,
        DEPARTMENT_REVIEWED,
        HOD_RECOMMENDED,
        AWAITING_FINAL_APPROVAL,
    }
)

# Stock transfer states (BW-PSM-08)
TRANSFER_REQUESTED = "requested"
TRANSFER_DISPATCHED = "dispatched"
TRANSFER_COMPLETED = "completed"
TRANSFER_CANCELLED = "cancelled"
TRANSFER_STATES = (
    TRANSFER_REQUESTED,
    TRANSFER_DISPATCHED,
    TRANSFER_COMPLETED,
    TRANSFER_CANCELLED,
)
TRANSFER_TERMINAL = frozenset({TRANSFER_COMPLETED, TRANSFER_CANCELLED})

# Discrepancy states (BW-PSM-06, BW-PSM-10)
DISC_OPEN = "open"
DISC_REPLACEMENT_AWAITED = "replacement_awaited"
DISC_RESOLVED = "resolved"
DISC_CLOSED = "closed"
DISCREPANCY_STATES = (DISC_OPEN, DISC_REPLACEMENT_AWAITED, DISC_RESOLVED, DISC_CLOSED)
DISCREPANCY_TERMINAL = frozenset({DISC_CLOSED})

# Invoice states (CW-PSM-02, BR-PSM-017, BR-PSM-018, BR-PSM-022)
INV_SUBMITTED = "submitted"
INV_VERIFIED = "verified"
INV_ON_HOLD = "on_hold"
INV_PARTIALLY_PAID = "partially_paid"
INV_PAID = "paid"
INVOICE_STATES = (INV_SUBMITTED, INV_VERIFIED, INV_ON_HOLD, INV_PARTIALLY_PAID, INV_PAID)
INVOICE_TERMINAL = frozenset({INV_PAID})

# Tender states (BW-PSM-05, BR-PSM-023)
TENDER_DRAFT = "draft"
TENDER_PUBLISHED = "published"
TENDER_EVALUATED = "evaluated"
TENDER_AWARDED_STATE = "awarded"
TENDER_CANCELLED = "cancelled"
TENDER_STATES = (
    TENDER_DRAFT,
    TENDER_PUBLISHED,
    TENDER_EVALUATED,
    TENDER_AWARDED_STATE,
    TENDER_CANCELLED,
)
TENDER_TERMINAL = frozenset({TENDER_AWARDED_STATE, TENDER_CANCELLED})

# Purchase order states (PSM-UC-025, PSM-UC-027, AFR-PSM-041, AFR-PSM-042)
PO_ISSUED = "issued"
PO_IN_TRANSIT = "in_transit"
PO_PARTIALLY_DELIVERED = "partially_delivered"
PO_DELIVERED = "delivered"
PO_CLOSED = "closed"
PO_CANCELLED = "cancelled"
PO_STATES = (
    PO_ISSUED,
    PO_IN_TRANSIT,
    PO_PARTIALLY_DELIVERED,
    PO_DELIVERED,
    PO_CLOSED,
    PO_CANCELLED,
)
PO_TERMINAL = frozenset({PO_CLOSED, PO_CANCELLED})

# Actor lanes
EMPLOYEE = "employee"
DEPT_ADMIN = "dept_admin"
DEPT_HEAD = "dept_head"
PS_ADMIN = "ps_admin"
FINAL_AUTHORITY = "final_authority"
ACCOUNTS = "accounts"
RECEIVING_ACTOR = "receiving_actor"


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


INDENT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(DRAFT, SUBMITTED, "psm.indent.create", frozenset({EMPLOYEE}), ("indent_complete",)),
    Transition(
        SUBMITTED, STOCK_RESERVED, "psm.stock.update", frozenset({DEPT_ADMIN}), ("stock_available",)
    ),
    Transition(
        SUBMITTED,
        EXTERNAL_REQUIRED,
        "psm.stock.update",
        frozenset({DEPT_ADMIN}),
        ("stock_insufficient",),
    ),
    Transition(
        STOCK_RESERVED,
        INTERNAL_APPROVED,
        "psm.indent.review",
        frozenset({DEPT_ADMIN}),
        ("not_self_actor",),
    ),
    Transition(
        STOCK_RESERVED,
        REJECTED,
        "psm.indent.review",
        frozenset({DEPT_ADMIN}),
        ("has_reason", "not_self_actor"),
    ),
    Transition(
        INTERNAL_APPROVED,
        DISPATCHED,
        "psm.stock.update",
        frozenset({DEPT_ADMIN}),
        ("reservation_active",),
    ),
    Transition(
        DISPATCHED,
        GRN_RECORDED,
        "psm.grn.create",
        frozenset({RECEIVING_ACTOR, EMPLOYEE, DEPT_ADMIN, DEPT_HEAD}),
        ("grn_accepted_or_partial",),
    ),
    Transition(
        GRN_RECORDED, FULFILLED, "psm.grn.approve", frozenset({EMPLOYEE}), ("no_open_discrepancy",)
    ),
    Transition(
        EXTERNAL_REQUIRED,
        DEPARTMENT_REVIEWED,
        "psm.indent.review",
        frozenset({DEPT_ADMIN}),
        ("not_self_actor",),
    ),
    Transition(
        EXTERNAL_REQUIRED,
        REJECTED,
        "psm.indent.review",
        frozenset({DEPT_ADMIN}),
        ("has_reason", "not_self_actor"),
    ),
    Transition(
        DEPARTMENT_REVIEWED,
        HOD_RECOMMENDED,
        "psm.indent.approve",
        frozenset({DEPT_HEAD}),
        ("not_self_actor",),
    ),
    Transition(
        DEPARTMENT_REVIEWED,
        CHANGES_REQUESTED,
        "psm.indent.approve",
        frozenset({DEPT_HEAD}),
        ("has_reason", "not_self_actor"),
    ),
    Transition(
        DEPARTMENT_REVIEWED,
        REJECTED,
        "psm.indent.approve",
        frozenset({DEPT_HEAD}),
        ("has_reason", "not_self_actor"),
    ),
    Transition(
        DEPARTMENT_REVIEWED,
        PROCUREMENT_AUTHORIZED,
        "psm.procurement.review",
        frozenset({PS_ADMIN}),
        ("high_priority_direct_permitted", "not_self_actor"),
    ),
    Transition(
        HOD_RECOMMENDED,
        PROCUREMENT_AUTHORIZED,
        "psm.procurement.review",
        frozenset({PS_ADMIN}),
        ("final_approval_not_required", "not_self_actor"),
    ),
    Transition(
        HOD_RECOMMENDED,
        AWAITING_FINAL_APPROVAL,
        "psm.procurement.review",
        frozenset({PS_ADMIN}),
        ("final_approval_required", "not_self_actor"),
    ),
    Transition(
        AWAITING_FINAL_APPROVAL,
        PROCUREMENT_AUTHORIZED,
        "psm.procurement.approve",
        frozenset({FINAL_AUTHORITY}),
        ("not_self_actor",),
    ),
    Transition(
        AWAITING_FINAL_APPROVAL,
        REJECTED,
        "psm.procurement.approve",
        frozenset({FINAL_AUTHORITY}),
        ("has_reason", "not_self_actor"),
    ),
    Transition(
        PROCUREMENT_AUTHORIZED,
        TENDER_AWARDED,
        "psm.tender.approve",
        frozenset({PS_ADMIN}),
        ("tender_method",),
    ),
    Transition(
        PROCUREMENT_AUTHORIZED,
        PO_ISSUED,
        "psm.purchase_order.create",
        frozenset({PS_ADMIN}),
        ("direct_method", "vendor_verified"),
    ),
    Transition(
        TENDER_AWARDED,
        PO_ISSUED,
        "psm.purchase_order.create",
        frozenset({PS_ADMIN}),
        ("vendor_verified",),
    ),
    Transition(
        PO_ISSUED,
        FULFILLED,
        "psm.grn.approve",
        frozenset({EMPLOYEE, ACCOUNTS}),
        ("all_qty_confirmed",),
    ),
    # BW-PSM-07 modification/resubmission and PSM-UC-005 withdrawal (policy-gated in service)
    *(
        Transition(
            s,
            SUBMITTED,
            "psm.indent.update",
            frozenset({EMPLOYEE}),
            ("state_modifiable", "indent_complete"),
        )
        for s in (SUBMITTED, CHANGES_REQUESTED, DEPARTMENT_REVIEWED)
    ),
    *(
        Transition(
            s, WITHDRAWN, "psm.indent.delete", frozenset({EMPLOYEE}), ("state_withdrawable",)
        )
        for s in (DRAFT, SUBMITTED, CHANGES_REQUESTED, DEPARTMENT_REVIEWED)
    ),
)

TRANSFER_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        TRANSFER_REQUESTED,
        TRANSFER_DISPATCHED,
        "psm.transfer.update",
        frozenset({DEPT_ADMIN, PS_ADMIN}),
        ("source_stock_available",),
    ),
    Transition(
        TRANSFER_DISPATCHED, TRANSFER_COMPLETED, "psm.transfer.approve", frozenset({DEPT_ADMIN}), ()
    ),
    Transition(
        TRANSFER_REQUESTED,
        TRANSFER_CANCELLED,
        "psm.transfer.delete",
        frozenset({DEPT_ADMIN, PS_ADMIN}),
        (),
    ),
)

DISCREPANCY_TRANSITIONS: tuple[Transition, ...] = (
    Transition(DISC_OPEN, DISC_RESOLVED, "psm.discrepancy.update", frozenset({PS_ADMIN}), ()),
    Transition(
        DISC_OPEN,
        DISC_REPLACEMENT_AWAITED,
        "psm.discrepancy.update",
        frozenset({PS_ADMIN}),
        ("replacement_count_zero",),
    ),
    Transition(
        DISC_REPLACEMENT_AWAITED,
        DISC_RESOLVED,
        "psm.grn.create",
        frozenset({RECEIVING_ACTOR, EMPLOYEE, DEPT_ADMIN, DEPT_HEAD, PS_ADMIN}),
        (),
    ),
    Transition(
        DISC_RESOLVED, DISC_CLOSED, "psm.discrepancy.update", frozenset({PS_ADMIN, ACCOUNTS}), ()
    ),
)

INVOICE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        INV_SUBMITTED,
        INV_VERIFIED,
        "psm.invoice.review",
        frozenset({ACCOUNTS}),
        ("three_way_match_passed",),
    ),
    Transition(
        INV_SUBMITTED, INV_ON_HOLD, "psm.invoice.review", frozenset({ACCOUNTS}), ("has_reason",)
    ),
    Transition(
        INV_ON_HOLD,
        INV_VERIFIED,
        "psm.invoice.review",
        frozenset({ACCOUNTS}),
        ("three_way_match_passed",),
    ),
    Transition(
        INV_VERIFIED, INV_ON_HOLD, "psm.invoice.review", frozenset({ACCOUNTS}), ("has_reason",)
    ),
    Transition(
        INV_VERIFIED,
        INV_PARTIALLY_PAID,
        "psm.payment.approve",
        frozenset({ACCOUNTS}),
        ("vendor_verified", "partial_payment_allowed"),
    ),
    Transition(
        INV_VERIFIED, INV_PAID, "psm.payment.approve", frozenset({ACCOUNTS}), ("vendor_verified",)
    ),
    Transition(
        INV_PARTIALLY_PAID,
        INV_PARTIALLY_PAID,
        "psm.payment.approve",
        frozenset({ACCOUNTS}),
        ("vendor_verified", "partial_payment_allowed"),
    ),
    Transition(
        INV_PARTIALLY_PAID,
        INV_PAID,
        "psm.payment.approve",
        frozenset({ACCOUNTS}),
        ("vendor_verified",),
    ),
)

TENDER_TRANSITIONS: tuple[Transition, ...] = (
    Transition(TENDER_DRAFT, TENDER_PUBLISHED, "psm.tender.publish", frozenset({PS_ADMIN}), ()),
    Transition(
        TENDER_PUBLISHED,
        TENDER_EVALUATED,
        "psm.tender.approve",
        frozenset({PS_ADMIN}),
        ("has_bids",),
    ),
    Transition(
        TENDER_EVALUATED,
        TENDER_AWARDED_STATE,
        "psm.tender.approve",
        frozenset({PS_ADMIN}),
        ("has_selected_bid",),
    ),
    Transition(TENDER_DRAFT, TENDER_CANCELLED, "psm.tender.publish", frozenset({PS_ADMIN}), ()),
    Transition(TENDER_PUBLISHED, TENDER_CANCELLED, "psm.tender.publish", frozenset({PS_ADMIN}), ()),
)

PO_TRANSITIONS: tuple[Transition, ...] = (
    Transition(PO_ISSUED, PO_IN_TRANSIT, "psm.purchase_order.update", frozenset({PS_ADMIN}), ()),
    Transition(
        PO_ISSUED,
        PO_PARTIALLY_DELIVERED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, RECEIVING_ACTOR}),
        (),
    ),
    Transition(
        PO_ISSUED,
        PO_DELIVERED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, RECEIVING_ACTOR}),
        (),
    ),
    Transition(PO_ISSUED, PO_CANCELLED, "psm.purchase_order.update", frozenset({PS_ADMIN}), ()),
    Transition(
        PO_IN_TRANSIT,
        PO_PARTIALLY_DELIVERED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, RECEIVING_ACTOR}),
        (),
    ),
    Transition(
        PO_IN_TRANSIT,
        PO_DELIVERED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, RECEIVING_ACTOR}),
        (),
    ),
    Transition(PO_IN_TRANSIT, PO_CANCELLED, "psm.purchase_order.update", frozenset({PS_ADMIN}), ()),
    Transition(
        PO_PARTIALLY_DELIVERED,
        PO_PARTIALLY_DELIVERED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, RECEIVING_ACTOR}),
        (),
    ),
    Transition(
        PO_PARTIALLY_DELIVERED,
        PO_DELIVERED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, RECEIVING_ACTOR}),
        (),
    ),
    Transition(
        PO_DELIVERED,
        PO_CLOSED,
        "psm.purchase_order.update",
        frozenset({PS_ADMIN, ACCOUNTS}),
        (),
    ),
)


def _index(table: tuple[Transition, ...]) -> dict[tuple[str, str], Transition]:
    return {(t.frm, t.to): t for t in table}


_TABLES = {
    "indent": _index(INDENT_TRANSITIONS),
    "transfer": _index(TRANSFER_TRANSITIONS),
    "discrepancy": _index(DISCREPANCY_TRANSITIONS),
    "invoice": _index(INVOICE_TRANSITIONS),
    "tender": _index(TENDER_TRANSITIONS),
    "purchase_order": _index(PO_TRANSITIONS),
}


def resolve(entity: str, frm: str, to: str, actor_lane: str | None = None) -> Transition:
    """Resolve and authorize a single transition from the declarative table."""
    table = _TABLES[entity]
    transition = table.get((frm, to))
    if transition is None:
        raise InvalidTransitionError(entity, frm, to)
    if actor_lane is not None and actor_lane not in transition.actors:
        raise ActorNotAllowedError(actor_lane, entity, frm, to)
    return transition


def is_legal(entity: str, frm: str, to: str) -> bool:
    """Return True iff (frm, to) is a declared transition for entity."""
    return (frm, to) in _TABLES[entity]
