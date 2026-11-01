"""Permissions this module recognises. No nav yet: backend-only slice (PS/UC/BR/WF v1.3)."""

PERMISSIONS = [
    ("iaa.request.create", "Create/submit expense-voucher requests and TA claims"),
    ("iaa.request.view", "View own requests and claims"),
    ("iaa.finance.review", "Review/validate requests, verify TA claims, run budget checks"),
    ("iaa.approval.decide", "Approve/reject routed requests and claims"),
    ("iaa.anomaly.manage", "Flag, resolve or escalate anomalies"),
    ("iaa.audit.manage", "Raise, respond to and close audit observations"),
]

SYSTEM_PERMISSIONS = []

_BASIC_USER = ["iaa.request.create", "iaa.request.view"]
_FINANCE_STAFF = _BASIC_USER + ["iaa.finance.review", "iaa.anomaly.manage"]
_APPROVING_AUTHORITY = _BASIC_USER + ["iaa.approval.decide"]
_AUDITOR = ["iaa.request.view", "iaa.audit.manage", "iaa.anomaly.manage"]

#: Keyed by the designation name as it exists in globals_designation.
#: PLACEHOLDER roles: replace with the designations that should apply/approve.
ROLE_GRANTS = {
    "faculty": _BASIC_USER,
    "finance_staff": _FINANCE_STAFF,
    "hod": _APPROVING_AUTHORITY,
    "dean": _APPROVING_AUTHORITY,
    "director": _APPROVING_AUTHORITY,
    "auditor": _AUDITOR,
}
