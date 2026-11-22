"""Server-discoverable IAA module metadata and permission catalogue."""

from modules.iaa.permissions import PERMISSIONS, ROLE_PERMISSIONS

MODULE = {
    "code": "iaa", "label": "Internal Audits and Accounts", "icon": "Receipt",
    "base_path": "/iaa", "nav_section": "Finance", "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "iaa.requests", "label": "Expense Requests", "icon": "Receipt",
     "to": "/iaa/expenses", "required_permission": "iaa.request.view", "sort_order": 10},
    {"code": "iaa.ta", "label": "Travel Claims", "icon": "Airplane",
     "to": "/iaa/ta", "required_permission": "iaa.ta.view", "sort_order": 20},
    {"code": "iaa.approvals", "label": "Approvals", "icon": "CheckCircle",
     "to": "/iaa/approvals", "required_permission": "iaa.approval.decide", "sort_order": 30},
    {"code": "iaa.audit", "label": "Audit Observations", "icon": "MagnifyingGlass",
     "to": "/iaa/audit", "required_permission": "iaa.audit.review", "sort_order": 40},
    {"code": "iaa.my-observations", "label": "My Audit Follow-ups", "icon": "ClipboardText",
     "to": "/iaa/audit", "required_permission": "iaa.observation.respond", "sort_order": 45},
    {"code": "iaa.configuration", "label": "IAA Configuration", "icon": "Gear",
     "to": "/iaa/configuration", "required_permission": "iaa.admin.configure", "sort_order": 55},
    {"code": "iaa.notifications", "label": "Notifications", "icon": "Bell",
     "to": "/iaa/notifications", "required_permission": "iaa.notification.view", "sort_order": 60},
    {"code": "iaa.anomalies", "label": "Anomalies", "icon": "Warning",
     "to": "/iaa/anomalies", "required_permission": "iaa.anomaly.resolve", "sort_order": 65},
    {"code": "iaa.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/iaa/reports", "required_permission": "iaa.report.view", "sort_order": 50},
]

_BASIC = ROLE_PERMISSIONS["basic_user"]
_FINANCE = ROLE_PERMISSIONS["finance_staff"]
_AUDITOR = ROLE_PERMISSIONS["auditor"]
_AUTHORITY = ROLE_PERMISSIONS["hod"]
_ADMIN = ROLE_PERMISSIONS["system_admin"]

# Designation strings must match Fusion IAM. Provision Basic User only for
# eligible institute employees; separate active-role selection is required.
_AUTHORITY_DESIGNATIONS = (
    "Director", "Dean Academic", "Dean (R&D)", "Dean (P&D)", "Dean_s",
    "HOD (CSE)", "HOD (ECE)", "HOD (ME)", "HOD (Design)", "HOD (NS)",
    "HOD (Liberal Arts)",
)
ROLE_GRANTS = {"Basic User": list(_BASIC)}
ROLE_GRANTS.update({name: list(_AUTHORITY) for name in _AUTHORITY_DESIGNATIONS})
ROLE_GRANTS["Finance Staff"] = list(_FINANCE)
ROLE_GRANTS["Auditor"] = list(_AUDITOR)
ROLE_GRANTS["System Admin"] = list(_ADMIN)
SYSTEM_PERMISSIONS = []
