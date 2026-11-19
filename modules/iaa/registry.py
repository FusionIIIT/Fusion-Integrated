"""Server-driven entry and the IAA actor permission catalogue."""

MODULE = {
    "code": "iaa",
    "label": "Institute Accounts and Audits",
    "icon": "FaFileInvoiceDollar",
    "base_path": "/iaa",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "iaa.requests", "label": "Expense / Voucher Requests",
     "icon": "FaReceipt", "to": "/iaa/requests",
     "required_permission": "iaa.request.view_self", "sort_order": 10},
    {"code": "iaa.finance", "label": "Finance Queue",
     "icon": "FaInbox", "to": "/iaa/finance",
     "required_permission": "iaa.request.review", "sort_order": 20},
    {"code": "iaa.approvals", "label": "Approvals",
     "icon": "FaCheckCircle", "to": "/iaa/approvals",
     "required_permission": "iaa.request.approve", "sort_order": 30},
    {"code": "iaa.ta", "label": "Travel Allowance",
     "icon": "FaPlane", "to": "/iaa/ta",
     "required_permission": "iaa.ta_claim.view_self", "sort_order": 40},
    {"code": "iaa.anomalies", "label": "Anomalies",
     "icon": "FaExclamationTriangle", "to": "/iaa/anomalies",
     "required_permission": "iaa.anomaly.view", "sort_order": 50},
    {"code": "iaa.audit", "label": "Audit Observations",
     "icon": "FaSearch", "to": "/iaa/audit-observations",
     "required_permission": "iaa.audit_observation.view", "sort_order": 60},
    {"code": "iaa.reports", "label": "Reports",
     "icon": "FaChartBar", "to": "/iaa/reports",
     "required_permission": "iaa.report.view", "sort_order": 70},
    {"code": "iaa.notifications", "label": "Notifications",
     "icon": "FaBell", "to": "/iaa/notifications",
     "required_permission": "iaa.notification.view", "sort_order": 75},
    {"code": "iaa.admin", "label": "Configuration",
     "icon": "FaCog", "to": "/iaa/configuration",
     "required_permission": "iaa.configuration.manage", "sort_order": 80},
]

PERMISSIONS = [
    ("iaa.request.view", "View requests within authorized scope"),
    ("iaa.request.view_self", "View own requests and their history"),
    ("iaa.request.create", "Create and submit expense or voucher requests"),
    ("iaa.request.update", "Update drafts or respond to a finance query"),
    ("iaa.request.review", "Review requests for finance validation"),
    ("iaa.request.approve", "Approve or reject assigned requests"),
    ("iaa.ta_claim.view", "View TA claims within authorized scope"),
    ("iaa.ta_claim.view_self", "View own TA claims and their history"),
    ("iaa.ta_claim.create", "Submit a TA claim"),
    ("iaa.ta_claim.update", "Respond to a TA clarification query"),
    ("iaa.ta_claim.review", "Verify TA claims for policy and budget compliance"),
    ("iaa.ta_claim.approve", "Approve or reject assigned high-value TA claims"),
    ("iaa.anomaly.view", "View anomalies within authorized scope"),
    ("iaa.anomaly.create", "Flag a material anomaly"),
    ("iaa.anomaly.update", "Resolve or escalate an assigned anomaly"),
    ("iaa.audit_record.view", "Review financial records for audit"),
    ("iaa.audit_observation.view", "View observations within authorized scope"),
    ("iaa.audit_observation.create", "Raise an audit observation"),
    ("iaa.audit_observation.update", "Respond to or verify an audit observation"),
    ("iaa.report.view", "View role-scoped IAA reports"),
    ("iaa.report.export", "Export a read-only IAA report"),
    ("iaa.notification.view", "View assigned IAA notifications and pending actions"),
    ("iaa.role.view", "View IAA role assignments"),
    ("iaa.role.update", "Select the active IAA actor role"),
    ("iaa.role.assign", "Manage IAA role assignments"),
    ("iaa.configuration.manage", "Configure IAA approval, budget, year, and policy rules"),
]

_BASIC_USER = [
    "iaa.request.view_self", "iaa.request.create", "iaa.request.update",
    "iaa.ta_claim.view_self", "iaa.ta_claim.create", "iaa.ta_claim.update",
    "iaa.audit_observation.view", "iaa.audit_observation.update",
    "iaa.notification.view", "iaa.role.view", "iaa.role.update",
]
_FINANCE = [
    "iaa.request.view", "iaa.request.review", "iaa.request.update",
    "iaa.request.approve",
    "iaa.ta_claim.view", "iaa.ta_claim.review", "iaa.ta_claim.update",
    "iaa.ta_claim.approve", "iaa.anomaly.view", "iaa.anomaly.create",
    "iaa.anomaly.update", "iaa.audit_record.view",
    "iaa.audit_observation.view", "iaa.report.view", "iaa.report.export",
    "iaa.notification.view", "iaa.role.view", "iaa.role.update",
]
_AUTHORITY = [
    "iaa.request.view", "iaa.request.approve", "iaa.ta_claim.view",
    "iaa.ta_claim.approve", "iaa.anomaly.view", "iaa.anomaly.update",
    "iaa.audit_record.view", "iaa.report.view",
    "iaa.notification.view", "iaa.role.view", "iaa.role.update",
]
_AUDITOR = [
    "iaa.request.view", "iaa.ta_claim.view", "iaa.anomaly.view",
    "iaa.anomaly.create", "iaa.anomaly.update",
    "iaa.audit_record.view", "iaa.audit_observation.view",
    "iaa.audit_observation.create", "iaa.audit_observation.update",
    "iaa.report.view", "iaa.report.export", "iaa.notification.view",
    "iaa.role.view", "iaa.role.update",
]

ROLE_GRANTS = {
    "Basic User": _BASIC_USER,
    "Finance Staff": _FINANCE,
    "HoD": _AUTHORITY,
    "Dean": _AUTHORITY,
    "Director": _AUTHORITY,
    "Auditor": _AUDITOR,
    # Separation rule: this role is limited to assignment and configuration.
    "System Admin": ["iaa.role.view", "iaa.role.update", "iaa.role.assign",
                      "iaa.configuration.manage"],
}

SYSTEM_PERMISSIONS = []
