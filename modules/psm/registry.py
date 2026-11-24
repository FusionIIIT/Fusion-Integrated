# Server-driven navigation and RBAC manifest for PSM (ADR-0010, BR-PSM-020).
MODULE = {
    "code": "psm",
    "label": "Procurement & Stores",
    "icon": "ShoppingCart",
    "base_path": "/psm",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "psm.dashboard",
        "label": "Dashboard",
        "icon": "Gauge",
        "to": "/psm/dashboard",
        "required_permission": "psm.dashboard.view",
        "sort_order": 5,
    },
    {
        "code": "psm.indents",
        "label": "Indents",
        "icon": "ClipboardText",
        "to": "/psm/indents",
        "required_permission": "psm.indent.view",
        "sort_order": 10,
    },
    {
        "code": "psm.stock",
        "label": "Stock & Issues",
        "icon": "Warehouse",
        "to": "/psm/stock",
        "required_permission": "psm.stock.view",
        "sort_order": 20,
    },
    {
        "code": "psm.transfers",
        "label": "Stock Transfers",
        "icon": "ArrowsLeftRight",
        "to": "/psm/transfers",
        "required_permission": "psm.transfer.view",
        "sort_order": 25,
    },
    {
        "code": "psm.vendors",
        "label": "Vendors",
        "icon": "Storefront",
        "to": "/psm/vendors",
        "required_permission": "psm.vendor.view",
        "sort_order": 30,
    },
    {
        "code": "psm.tenders",
        "label": "Tenders",
        "icon": "Gavel",
        "to": "/psm/tenders",
        "required_permission": "psm.tender.view",
        "sort_order": 35,
    },
    {
        "code": "psm.purchase_orders",
        "label": "Purchase Orders",
        "icon": "FileText",
        "to": "/psm/purchase-orders",
        "required_permission": "psm.purchase_order.view",
        "sort_order": 40,
    },
    {
        "code": "psm.grns",
        "label": "Receipts & Discrepancies",
        "icon": "Package",
        "to": "/psm/receipts",
        "required_permission": "psm.grn.view",
        "sort_order": 45,
    },
    {
        "code": "psm.invoices",
        "label": "Invoices & Payments",
        "icon": "Receipt",
        "to": "/psm/invoices",
        "required_permission": "psm.invoice.view",
        "sort_order": 50,
    },
    {
        "code": "psm.reports",
        "label": "Reports",
        "icon": "ChartBar",
        "to": "/psm/reports",
        "required_permission": "psm.report.view",
        "sort_order": 60,
    },
    {
        "code": "psm.audit",
        "label": "Audit Trail",
        "icon": "ShieldCheck",
        "to": "/psm/audit",
        "required_permission": "psm.audit.view",
        "sort_order": 70,
    },
    {
        "code": "psm.policy",
        "label": "Policy",
        "icon": "Sliders",
        "to": "/psm/policy",
        "required_permission": "psm.policy.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("psm.dashboard.view", "View Procurement & Stores dashboard"),
    ("psm.indent.view", "View indents within authorized scope"),
    ("psm.indent.create", "Create, submit, and repeat purchase indents"),
    ("psm.indent.update", "Modify own pending indents in permissible states"),
    ("psm.indent.delete", "Withdraw or cancel own pending indents"),
    ("psm.indent.review", "Review indents, set priority, and approve internal issue"),
    ("psm.indent.approve", "Recommend, request changes on, or reject departmental indents"),
    ("psm.stock.view", "View departmental and central stock availability"),
    ("psm.stock.update", "Reserve stock, dispatch internal issues, and post adjustments"),
    ("psm.transfer.view", "View inter-departmental stock transfers"),
    ("psm.transfer.create", "Request an inter-departmental stock transfer"),
    ("psm.transfer.update", "Reserve and dispatch an outgoing stock transfer"),
    ("psm.transfer.approve", "Confirm receipt of an incoming stock transfer"),
    ("psm.transfer.delete", "Cancel a pending stock transfer request"),
    ("psm.vendor.view", "View vendor master records and version history"),
    ("psm.vendor.create", "Onboard new vendors"),
    ("psm.vendor.update", "Update vendor master data and verification status"),
    ("psm.procurement.review", "Review external procurements and select procurement method"),
    ("psm.procurement.approve", "Grant final Director/Registrar approval on high-value indents"),
    ("psm.tender.view", "View tenders and recorded bids"),
    ("psm.tender.create", "Create tenders and record vendor bids"),
    ("psm.tender.publish", "Publish tender invitations"),
    ("psm.tender.approve", "Record bid evaluations and committee tender award"),
    ("psm.purchase_order.view", "View purchase orders and delivery schedules"),
    ("psm.purchase_order.create", "Create and issue purchase orders"),
    ("psm.purchase_order.update", "Update purchase order status and delivery schedules"),
    ("psm.grn.view", "View goods receipt notes and delivery discrepancies"),
    ("psm.grn.create", "Inspect deliveries, record GRNs, and report discrepancies"),
    ("psm.grn.approve", "Confirm delivery receipt and trigger final stock posting"),
    ("psm.discrepancy.update", "Record vendor communications and resolve discrepancy cases"),
    ("psm.invoice.view", "View vendor invoices and payment status"),
    ("psm.invoice.create", "Record vendor invoices against purchase orders"),
    ("psm.invoice.review", "Perform three-way invoice matching and place/release holds"),
    ("psm.payment.approve", "Process and release eligible vendor payments"),
    ("psm.report.view", "Generate and view operational, procurement, and stock reports"),
    ("psm.report.export", "Export reports and audit extracts"),
    ("psm.report.create", "Create and manage scheduled report definitions"),
    ("psm.financial_report.view", "Generate and view financial procurement reports"),
    ("psm.audit.view", "Access internal and statutory audit records"),
    ("psm.policy.view", "View active and historical PSM policy versions"),
    ("psm.policy.create", "Publish a new effective-dated PSM policy version"),
    ("psm.sla.review", "System SLA reminder and escalation sweep"),
    ("psm.report.publish", "System scheduled report execution"),
]

SYSTEM_PERMISSIONS = [
    "psm.sla.review",
    "psm.report.publish",
]

SCOPE_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.indent.create",
    "psm.indent.update",
    "psm.indent.delete",
    "psm.grn.view",
    "psm.grn.create",
    "psm.grn.approve",
]

_STAFF_EMPLOYEE = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.indent.create",
    "psm.indent.update",
    "psm.indent.delete",
]

_DEPT_ADMIN = [
    *_EMPLOYEE,
    "psm.indent.review",
    "psm.stock.view",
    "psm.stock.update",
    "psm.transfer.view",
    "psm.transfer.create",
    "psm.transfer.update",
    "psm.transfer.approve",
    "psm.transfer.delete",
    "psm.report.view",
    "psm.report.export",
    "psm.report.create",
]

_HOD = [
    *_EMPLOYEE,
    "psm.indent.approve",
    "psm.stock.view",
    "psm.report.view",
]

_PS_ADMIN = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.stock.view",
    "psm.stock.update",
    "psm.transfer.view",
    "psm.transfer.update",
    "psm.vendor.view",
    "psm.vendor.create",
    "psm.vendor.update",
    "psm.procurement.review",
    "psm.tender.view",
    "psm.tender.create",
    "psm.tender.publish",
    "psm.tender.approve",
    "psm.purchase_order.view",
    "psm.purchase_order.create",
    "psm.purchase_order.update",
    "psm.grn.view",
    "psm.discrepancy.update",
    "psm.invoice.view",
    "psm.invoice.create",
    "psm.report.view",
    "psm.report.export",
    "psm.report.create",
    "psm.policy.view",
    "psm.policy.create",
]

_FINAL_AUTHORITY = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.procurement.approve",
    "psm.purchase_order.view",
    "psm.report.view",
    "psm.financial_report.view",
    "psm.policy.view",
]

_ACCOUNTS = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.vendor.view",
    "psm.purchase_order.view",
    "psm.grn.view",
    "psm.invoice.view",
    "psm.invoice.create",
    "psm.invoice.review",
    "psm.payment.approve",
    "psm.report.view",
    "psm.report.export",
    "psm.report.create",
    "psm.financial_report.view",
    "psm.audit.view",
]

_AUDITOR = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.stock.view",
    "psm.transfer.view",
    "psm.vendor.view",
    "psm.tender.view",
    "psm.purchase_order.view",
    "psm.grn.view",
    "psm.invoice.view",
    "psm.report.view",
    "psm.report.export",
    "psm.financial_report.view",
    "psm.audit.view",
    "psm.policy.view",
]

# Keyed by exact designation names in globals_designation plus basic roles.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _STAFF_EMPLOYEE,
    "dept_admin": _DEPT_ADMIN,
    "deptadmin_cse": _DEPT_ADMIN,
    "deptadmin_design": _DEPT_ADMIN,
    "deptadmin_ece": _DEPT_ADMIN,
    "deptadmin_liberalarts": _DEPT_ADMIN,
    "deptadmin_me": _DEPT_ADMIN,
    "deptadmin_ns": _DEPT_ADMIN,
    "deptadmin_sm": _DEPT_ADMIN,
    "HOD (CSE)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (Liberal Arts)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (NS)": _HOD,
    "ps_admin": _PS_ADMIN,
    "SectionHead_PS": _PS_ADMIN,
    "Director": _FINAL_AUTHORITY,
    "Registrar": _FINAL_AUTHORITY,
    "Accounts Admin": _ACCOUNTS,
    "Auditor": _AUDITOR,
}


def readiness() -> list[str]:
    """Return unmet operational prerequisites as actionable sentences."""
    from modules.psm.models import PsmPolicy

    missing: list[str] = []
    if not PsmPolicy.objects.filter(is_active=True).exists():
        missing.append("No active PSM policy is configured; run 'manage.py seed_psm_policy'.")
    return missing
