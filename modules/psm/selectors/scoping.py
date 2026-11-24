# Role-based queryset scoping for PSM; out-of-scope IDs yield 404 (BR-PSM-020).
from __future__ import annotations

from django.db.models import Exists, OuterRef, Q, QuerySet

from modules.directory import contracts as directory
from modules.psm.domain import state_machine as sm
from modules.psm.models import (
    DiscrepancyCase,
    GoodsReceiptNote,
    Indent,
    InternalIssue,
    Invoice,
    PsmAuditLog,
    PsmNotification,
    PsmPolicy,
    PurchaseOrder,
    ReportGenerationLog,
    ReportSchedule,
    StockItem,
    StockLocation,
    StockTransfer,
    Tender,
    Vendor,
)

INSTITUTE_WIDE_ROLES = frozenset(
    {
        "ps_admin",
        "SectionHead_PS",
        "Director",
        "Registrar",
        "Accounts Admin",
        "Auditor",
    }
)

DEPT_ROLE_MAP = {
    "deptadmin_cse": "CSE",
    "deptadmin_design": "Design",
    "deptadmin_ece": "ECE",
    "deptadmin_liberalarts": "Liberal Arts",
    "deptadmin_me": "ME",
    "deptadmin_ns": "NS",
    "deptadmin_sm": "SM",
    "HOD (CSE)": "CSE",
    "HOD (Design)": "Design",
    "HOD (ECE)": "ECE",
    "HOD (Liberal Arts)": "Liberal Arts",
    "HOD (ME)": "ME",
    "HOD (NS)": "NS",
}

DEPT_ADMIN_ROLES = frozenset(
    {"dept_admin", *(r for r in DEPT_ROLE_MAP if r.startswith("deptadmin_"))}
)
HOD_ROLES = frozenset(r for r in DEPT_ROLE_MAP if r.startswith("HOD "))


def active_role_of(actor) -> str:
    """Return the single acting role on the principal."""
    return (getattr(actor, "active_role", None) or "").strip()


def is_institute_wide(actor) -> bool:
    """Return True only when the acting role has institute-wide PSM scope."""
    return active_role_of(actor) in INSTITUTE_WIDE_ROLES


def actor_department(actor) -> str | None:
    """Resolve the acting role's department, falling back to directory UserRef.department."""
    role = active_role_of(actor)
    if role in DEPT_ROLE_MAP:
        return DEPT_ROLE_MAP[role]
    if role == "dept_admin":
        uid = getattr(actor, "user_id", None)
        if uid is None:
            return None
        ref = directory.get_users([uid]).get(uid)
        dept = (getattr(ref, "department", "") or "").strip()
        return dept or None
    return None


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def indents_for(actor) -> QuerySet[Indent]:
    """Scope indents by acting role and annotate active discrepancy status."""
    open_disc = DiscrepancyCase.objects.filter(
        status__in=(sm.DISC_OPEN, sm.DISC_REPLACEMENT_AWAITED)
    ).filter(
        Q(grn__purchase_order__indent_id=OuterRef("pk"))
        | Q(grn__internal_issue__indent_id=OuterRef("pk"))
    )
    base = Indent.objects.select_related("item", "policy").annotate(
        has_open_discrepancy=Exists(open_disc)
    )
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    own = _own_id(actor)
    if dept:
        return (
            base.filter(Q(department__iexact=dept) | Q(user_id=own))
            if own is not None
            else base.filter(department__iexact=dept)
        )
    return base.filter(user_id=own) if own is not None else base.none()


def open_discrepancies_by_indent(indent_ids: list[int]) -> dict[int, list[dict]]:
    """Batch-fetch active discrepancy summaries keyed by indent_id in a single query."""
    if not indent_ids:
        return {}
    rows = (
        DiscrepancyCase.objects.filter(status__in=(sm.DISC_OPEN, sm.DISC_REPLACEMENT_AWAITED))
        .filter(
            Q(grn__purchase_order__indent_id__in=indent_ids)
            | Q(grn__internal_issue__indent_id__in=indent_ids)
        )
        .values(
            "id",
            "case_number",
            "status",
            "discrepancy_type",
            "grn__purchase_order__indent_id",
            "grn__internal_issue__indent_id",
        )
    )
    grouped: dict[int, list[dict]] = {}
    for r in rows:
        iid = r["grn__purchase_order__indent_id"] or r["grn__internal_issue__indent_id"]
        if iid is None:
            continue
        grouped.setdefault(iid, []).append(
            {
                "id": r["id"],
                "case_number": r["case_number"],
                "status": r["status"],
                "discrepancy_type": r["discrepancy_type"],
            }
        )
    return grouped


def stock_locations_for(actor) -> QuerySet[StockLocation]:
    """Expose central stores plus the caller's department locations."""
    base = StockLocation.objects.all()
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    if dept:
        return base.filter(Q(is_central=True) | Q(department__iexact=dept))
    return base.filter(is_central=True)


def internal_issues_for(actor) -> QuerySet[InternalIssue]:
    """Scope internal stock issues to visible indents."""
    base = InternalIssue.objects.select_related("indent", "location", "reservation", "indent__item")
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    own = _own_id(actor)
    if dept:
        return base.filter(Q(indent__department__iexact=dept) | Q(indent__user_id=own))
    return base.filter(indent__user_id=own) if own is not None else base.none()


def transfers_for(actor) -> QuerySet[StockTransfer]:
    """Scope inter-departmental stock transfers to source or destination department."""
    base = StockTransfer.objects.select_related(
        "item", "source_location", "destination_location", "reservation"
    )
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    if dept:
        return base.filter(
            Q(source_location__department__iexact=dept)
            | Q(destination_location__department__iexact=dept)
        )
    return base.none()


def vendors_for(actor) -> QuerySet[Vendor]:
    """Expose vendor master only to roles holding vendor view permission."""
    if getattr(actor, "has_permission", lambda _: False)("psm.vendor.view"):
        return Vendor.objects.all()
    return Vendor.objects.none()


def tenders_for(actor) -> QuerySet[Tender]:
    """Expose tenders only to roles holding tender view permission."""
    if getattr(actor, "has_permission", lambda _: False)("psm.tender.view"):
        return Tender.objects.select_related("indent", "awarded_vendor").prefetch_related(
            "bids", "bids__vendor"
        )
    return Tender.objects.none()


def purchase_orders_for(actor) -> QuerySet[PurchaseOrder]:
    """Scope purchase orders by acting role."""
    base = PurchaseOrder.objects.select_related("indent", "vendor", "tender")
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    own = _own_id(actor)
    if dept:
        return base.filter(Q(indent__department__iexact=dept) | Q(indent__user_id=own))
    return base.filter(indent__user_id=own) if own is not None else base.none()


def grns_for(actor) -> QuerySet[GoodsReceiptNote]:
    """Scope GRNs to deliveries visible to the caller."""
    base = GoodsReceiptNote.objects.select_related(
        "purchase_order",
        "purchase_order__indent",
        "purchase_order__vendor",
        "internal_issue",
        "internal_issue__indent",
        "replacement_for_case",
    )
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    own = _own_id(actor)
    if dept:
        return base.filter(
            Q(purchase_order__indent__department__iexact=dept)
            | Q(internal_issue__indent__department__iexact=dept)
            | Q(purchase_order__indent__user_id=own)
            | Q(internal_issue__indent__user_id=own)
        )
    if own is None:
        return base.none()
    return base.filter(
        Q(purchase_order__indent__user_id=own) | Q(internal_issue__indent__user_id=own)
    )


def discrepancies_for(actor) -> QuerySet[DiscrepancyCase]:
    """Scope discrepancy cases to visible GRNs."""
    base = DiscrepancyCase.objects.select_related(
        "grn",
        "grn__purchase_order",
        "grn__purchase_order__indent",
        "grn__internal_issue",
        "grn__internal_issue__indent",
    ).prefetch_related("communications")
    if is_institute_wide(actor):
        return base
    dept = actor_department(actor)
    own = _own_id(actor)
    if dept:
        return base.filter(
            Q(grn__purchase_order__indent__department__iexact=dept)
            | Q(grn__internal_issue__indent__department__iexact=dept)
            | Q(reported_by_user_id=own)
        )
    if own is None:
        return base.none()
    return base.filter(
        Q(grn__purchase_order__indent__user_id=own)
        | Q(grn__internal_issue__indent__user_id=own)
        | Q(reported_by_user_id=own)
    )


def invoices_for(actor) -> QuerySet[Invoice]:
    """Expose invoices only to institute-wide roles holding invoice view permission."""
    if is_institute_wide(actor) and getattr(actor, "has_permission", lambda _: False)(
        "psm.invoice.view"
    ):
        return Invoice.objects.select_related(
            "purchase_order", "purchase_order__indent", "vendor"
        ).prefetch_related("payments")
    return Invoice.objects.none()


def audit_logs_for(actor) -> QuerySet[PsmAuditLog]:
    """Expose audit trail only to roles holding audit view permission (PSM-UC-014)."""
    if getattr(actor, "has_permission", lambda _: False)("psm.audit.view"):
        return PsmAuditLog.objects.all()
    return PsmAuditLog.objects.none()


def notifications_for(actor) -> QuerySet[PsmNotification]:
    """Return only the caller's own communication history (BR-PSM-006)."""
    own = _own_id(actor)
    return (
        PsmNotification.objects.filter(recipient_user_id=own)
        if own is not None
        else PsmNotification.objects.none()
    )


def report_schedules_for(actor) -> QuerySet[ReportSchedule]:
    """Scope report schedules to institute-wide roles or caller's own definitions."""
    base = ReportSchedule.objects.all()
    if is_institute_wide(actor):
        return base
    own = _own_id(actor)
    return base.filter(created_by_user_id=own) if own is not None else base.none()


def report_logs_for(actor) -> QuerySet[ReportGenerationLog]:
    """Scope report generation logs by role, financial permission, and schedule ownership."""
    base = ReportGenerationLog.objects.select_related("schedule")
    if not getattr(actor, "has_permission", lambda _: False)("psm.financial_report.view"):
        base = base.exclude(report_type="financial")
    if is_institute_wide(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(Q(schedule__created_by_user_id=own) | Q(actor_user_id=own))


def active_stock_items() -> QuerySet[StockItem]:
    """Return all active catalog stock items."""
    return StockItem.objects.filter(is_active=True)


def all_policies() -> QuerySet[PsmPolicy]:
    """Return effective-dated PSM policies newest first."""
    return PsmPolicy.objects.all()
