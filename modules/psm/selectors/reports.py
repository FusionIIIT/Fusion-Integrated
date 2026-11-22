# Scoped report query builders for operational, procurement, stock, and financial reports.
from __future__ import annotations

from modules.psm.selectors import scoping
from modules.psm.selectors import stock as stock_sel

_OPERATIONAL_HEADERS = [
    "indent_number",
    "department",
    "item_description",
    "quantity",
    "estimated_cost",
    "priority",
    "status",
    "procurement_method",
]
_PROCUREMENT_HEADERS = [
    "po_number",
    "indent_number",
    "department",
    "vendor_name",
    "ordered_quantity",
    "total_amount",
    "status",
    "planned_delivery_date",
]
_STOCK_HEADERS = [
    "sku",
    "item_name",
    "location_code",
    "department",
    "on_hand",
    "reserved",
    "allocable",
]
_FINANCIAL_HEADERS = [
    "invoice_number",
    "po_number",
    "vendor_name",
    "billed_amount",
    "eligible_amount",
    "status",
    "hold_reason",
]


def _operational_rows(actor, department: str, status: str) -> tuple[list[str], list[dict]]:
    qs = scoping.indents_for(actor)
    if department:
        qs = qs.filter(department__iexact=department)
    if status:
        qs = qs.filter(status=status)
    rows = [
        {
            "indent_number": i.indent_number or f"DRAFT-{i.pk}",
            "department": i.department,
            "item_description": i.item_description,
            "quantity": i.quantity,
            "estimated_cost": str(i.estimated_cost),
            "priority": i.priority,
            "status": i.status,
            "procurement_method": i.procurement_method,
        }
        for i in qs[:500]
    ]
    return list(_OPERATIONAL_HEADERS), rows


def _procurement_rows(actor, department: str, status: str) -> tuple[list[str], list[dict]]:
    qs = scoping.purchase_orders_for(actor)
    if department:
        qs = qs.filter(indent__department__iexact=department)
    if status:
        qs = qs.filter(status=status)
    rows = [
        {
            "po_number": po.po_number,
            "indent_number": po.indent.indent_number or f"DRAFT-{po.indent_id}",
            "department": po.indent.department,
            "vendor_name": po.vendor.name,
            "ordered_quantity": po.ordered_quantity,
            "total_amount": str(po.total_amount),
            "status": po.status,
            "planned_delivery_date": po.planned_delivery_date.isoformat(),
        }
        for po in qs[:500]
    ]
    return list(_PROCUREMENT_HEADERS), rows


def _stock_rows(actor, department: str) -> tuple[list[str], list[dict]]:
    raw = stock_sel.availability_rows(actor)
    if department:
        raw = [r for r in raw if r["department"].lower() == department.lower()]
    return list(_STOCK_HEADERS), [{k: r[k] for k in _STOCK_HEADERS} for r in raw]


def _financial_rows(actor, department: str, status: str) -> tuple[list[str], list[dict]]:
    qs = scoping.invoices_for(actor)
    if department:
        qs = qs.filter(purchase_order__indent__department__iexact=department)
    if status:
        qs = qs.filter(status=status)
    rows = [
        {
            "invoice_number": inv.invoice_number,
            "po_number": inv.purchase_order.po_number,
            "vendor_name": inv.vendor.name,
            "billed_amount": str(inv.billed_amount),
            "eligible_amount": str(inv.eligible_amount),
            "status": inv.status,
            "hold_reason": inv.hold_reason,
        }
        for inv in qs[:500]
    ]
    return list(_FINANCIAL_HEADERS), rows


def build_report_rows(actor, *, report_type: str, filters: dict) -> tuple[list[str], list[dict]]:
    """Build filtered report headers and rows strictly within the caller's scope."""
    department = (filters.get("department") or "").strip()
    status = (filters.get("status") or "").strip()
    if report_type == "operational":
        return _operational_rows(actor, department, status)
    if report_type == "procurement":
        return _procurement_rows(actor, department, status)
    if report_type == "stock":
        return _stock_rows(actor, department)
    return _financial_rows(actor, department, status)
