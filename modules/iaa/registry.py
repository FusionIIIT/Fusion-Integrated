"""What the server tells the shell about IAA; nav is filtered per role before it is sent."""
from modules.iaa.domain import roles

MODULE = {
    "code": "iaa", "label": "Accounts & Audits", "icon": "Calculator",
    "base_path": "/iaa", "nav_section": "Finance", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "iaa.my_requests", "label": "My Requests & TA", "icon": "Receipt",
     "to": "/iaa/my-requests", "required_permission": "iaa.request.create", "sort_order": 10},
    {"code": "iaa.finance", "label": "Finance Review", "icon": "ListChecks",
     "to": "/iaa/finance", "required_permission": "iaa.request.review", "sort_order": 20},
    {"code": "iaa.approvals", "label": "Approvals", "icon": "Stamp",
     "to": "/iaa/approvals", "required_permission": "iaa.request.approve", "sort_order": 30},
    {"code": "iaa.anomalies", "label": "Anomalies", "icon": "WarningOctagon",
     "to": "/iaa/anomalies", "required_permission": "iaa.anomaly.view", "sort_order": 40},
    {"code": "iaa.observations", "label": "Audit Observations", "icon": "MagnifyingGlass",
     "to": "/iaa/observations", "required_permission": "iaa.observation.view",
     "sort_order": 50},
    {"code": "iaa.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/iaa/reports", "required_permission": "iaa.report.view", "sort_order": 60},
    {"code": "iaa.notifications", "label": "Notifications", "icon": "Bell",
     "to": "/iaa/notifications", "required_permission": "iaa.notification.view",
     "sort_order": 70},
    {"code": "iaa.configuration", "label": "Configuration", "icon": "GearSix",
     "to": "/iaa/configuration", "required_permission": "iaa.configuration.view",
     "sort_order": 80},
]

PERMISSIONS = [
    ("iaa.request.view", "See requests and TA claims within your role's scope"),
    ("iaa.request.create", "Create, submit and track your own requests and TA claims"),
    ("iaa.clarification.update", "Answer Finance's clarification queries on your own items"),
    ("iaa.request.review", "Validate requests and verify TA claims (Finance)"),
    ("iaa.request.approve", "Approve or reject items assigned to your authority role"),
    ("iaa.processing.create", "Record internal processing of approved items (no payment)"),
    ("iaa.anomaly.view", "See anomalies within your role's scope"),
    ("iaa.anomaly.create", "Flag a material anomaly"),
    ("iaa.anomaly.review", "Resolve or escalate an anomaly assigned to your role"),
    ("iaa.observation.view", "See audit observations within your role's scope"),
    ("iaa.observation.create", "Raise an audit observation"),
    ("iaa.observation.update", "Respond to an audit observation addressed to you"),
    ("iaa.observation.review", "Verify a response and close or return an observation"),
    ("iaa.report.view", "See role-scoped IAA reports"),
    ("iaa.report.export", "Export role-scoped IAA reports"),
    ("iaa.notification.view", "See IAA notifications and pending actions"),
    ("iaa.configuration.view", "See IAA configuration"),
    ("iaa.configuration.update", "Publish policy, financial years and budget entries"),
    ("iaa.approval.assign", "System escalation of overdue approvals"),
]

SYSTEM_PERMISSIONS = [
    "iaa.approval.assign",
]

_BASIC = [
    "iaa.request.view",
    "iaa.request.create",
    "iaa.clarification.update",
    "iaa.observation.view",
    "iaa.observation.update",
    "iaa.notification.view",
]

_FINANCE = [
    "iaa.request.view",
    "iaa.request.review",
    "iaa.processing.create",
    "iaa.anomaly.view",
    "iaa.anomaly.create",
    "iaa.anomaly.review",
    "iaa.observation.view",
    "iaa.report.view",
    "iaa.report.export",
    "iaa.notification.view",
]

_APPROVER = [
    "iaa.request.view",
    "iaa.request.approve",
    "iaa.anomaly.view",
    "iaa.anomaly.review",
    "iaa.report.view",
    "iaa.report.export",
    "iaa.notification.view",
]

_AUDITOR = [
    "iaa.request.view",
    "iaa.anomaly.view",
    "iaa.anomaly.create",
    "iaa.anomaly.review",
    "iaa.observation.view",
    "iaa.observation.create",
    "iaa.observation.review",
    "iaa.report.view",
    "iaa.report.export",
    "iaa.notification.view",
]

# Configuration only: no operational code at all (IAA-BR-004).
_SYSTEM_ADMIN = [
    "iaa.configuration.view",
    "iaa.configuration.update",
]

ROLE_GRANTS = {
    "faculty": _BASIC,
    "staff": _BASIC,
    roles.FINANCE: _FINANCE,
    roles.HOD: _APPROVER,
    roles.DEAN: _APPROVER,
    roles.DIRECTOR: _APPROVER,
    roles.AUDITOR: _AUDITOR,
    roles.SYSTEM_ADMIN: _SYSTEM_ADMIN,
}
