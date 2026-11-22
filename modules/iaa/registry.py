"""IAA module declaration for the shell registry."""

MODULE = {
    "code": "iaa",
    "label": "Institute Accounts & Audits",
    "icon": "Receipt",
    "base_path": "/iaa",
    "nav_section": "Administration",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "iaa.requests",
        "label": "Expense & Vouchers",
        "icon": "FileText",
        "to": "/iaa/requests",
        "required_permission": "iaa.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "iaa.travel",
        "label": "Travel Claims",
        "icon": "AirplaneTilt",
        "to": "/iaa/travel",
        "required_permission": "iaa.travel.view_self",
        "sort_order": 20,
    },
    {
        "code": "iaa.approvals",
        "label": "Approval Queue",
        "icon": "CheckSquareOffset",
        "to": "/iaa/approvals",
        "required_permission": "iaa.request.approve",
        "sort_order": 30,
    },
    {
        "code": "iaa.anomalies",
        "label": "Anomalies",
        "icon": "WarningCircle",
        "to": "/iaa/anomalies",
        "required_permission": "iaa.anomaly.view",
        "sort_order": 40,
    },
    {
        "code": "iaa.audit",
        "label": "Audit Observations",
        "icon": "ShieldCheck",
        "to": "/iaa/audit",
        "required_permission": "iaa.audit.view",
        "sort_order": 50,
    },
    {
        "code": "iaa.reports",
        "label": "Reports & Analytics",
        "icon": "ChartBar",
        "to": "/iaa/reports",
        "required_permission": "iaa.report.view",
        "sort_order": 60,
    },
    {
        "code": "iaa.config",
        "label": "IAA Configuration",
        "icon": "GearSix",
        "to": "/iaa/config",
        "required_permission": "iaa.config.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("iaa.request.create", "Create and submit expense/voucher requests"),
    ("iaa.request.view_self", "View one's own expense/voucher requests"),
    ("iaa.request.view_all", "View all expense/voucher requests"),
    ("iaa.request.validate", "Validate financial documents and budget availability"),
    ("iaa.request.approve", "Record approval or rejection decisions on requests"),
    ("iaa.request.record", "Record internal governance completion of requests"),
    ("iaa.travel.create", "Create and submit travel allowance claims"),
    ("iaa.travel.view_self", "View one's own travel allowance claims"),
    ("iaa.travel.view_all", "View all travel allowance claims"),
    ("iaa.travel.verify", "Verify travel claims and documentary evidence"),
    ("iaa.travel.approve", "Approve or reject high-value travel claims"),
    ("iaa.travel.record", "Record internal governance completion of travel claims"),
    ("iaa.anomaly.view", "View flagged anomalies"),
    ("iaa.anomaly.flag", "Flag material anomalies manually"),
    ("iaa.anomaly.resolve", "Resolve or escalate material anomalies"),
    ("iaa.audit.view", "View audit observations and audit review data"),
    ("iaa.audit.raise", "Raise audit observations"),
    ("iaa.audit.respond", "Submit response and evidence to audit observations"),
    ("iaa.audit.close", "Verify response and close audit observations"),
    ("iaa.report.view", "View financial status reports and dashboards"),
    ("iaa.config.manage", "Configure approval hierarchy, thresholds, and parameters"),
    ("iaa.approval.timeout_escalate", "Autonomous system approval timeout escalation"),
    ("iaa.anomaly.auto_create", "Autonomous system anomaly creation"),
]

SYSTEM_PERMISSIONS = [
    "iaa.approval.timeout_escalate",
    "iaa.anomaly.auto_create",
]

_BASIC_USER = [
    "iaa.request.create",
    "iaa.request.view_self",
    "iaa.travel.create",
    "iaa.travel.view_self",
    "iaa.audit.respond",
]

_FINANCE_STAFF = [
    "iaa.request.create",
    "iaa.request.view_self",
    "iaa.request.view_all",
    "iaa.request.validate",
    "iaa.request.record",
    "iaa.travel.create",
    "iaa.travel.view_self",
    "iaa.travel.view_all",
    "iaa.travel.verify",
    "iaa.travel.record",
    "iaa.anomaly.view",
    "iaa.anomaly.flag",
    "iaa.anomaly.resolve",
    "iaa.report.view",
]

_APPROVING_AUTHORITY = [
    "iaa.request.create",
    "iaa.request.view_self",
    "iaa.request.view_all",
    "iaa.request.approve",
    "iaa.travel.create",
    "iaa.travel.view_self",
    "iaa.travel.view_all",
    "iaa.travel.approve",
    "iaa.anomaly.view",
    "iaa.anomaly.resolve",
    "iaa.report.view",
]

_AUDITOR = [
    "iaa.request.view_all",
    "iaa.travel.view_all",
    "iaa.anomaly.view",
    "iaa.anomaly.flag",
    "iaa.audit.view",
    "iaa.audit.raise",
    "iaa.audit.close",
    "iaa.report.view",
]

_SYSTEM_ADMIN = [
    "iaa.config.manage",
]

ROLE_GRANTS = {
    "student": _BASIC_USER,
    "faculty": _BASIC_USER,
    "staff": _BASIC_USER,
    "finance_staff": _FINANCE_STAFF,
    "HOD": _APPROVING_AUTHORITY,
    "Dean": _APPROVING_AUTHORITY,
    "Director": _APPROVING_AUTHORITY,
    "auditor": _AUDITOR,
    "admin": _SYSTEM_ADMIN,
    "system_admin": _SYSTEM_ADMIN,
}
