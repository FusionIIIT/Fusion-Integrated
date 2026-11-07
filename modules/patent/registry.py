"""What the server tells the shell about this module (ADR-0010).

PMS nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "patent", "label": "Patent Management", "icon": "FileText",
    "base_path": "/patent", "nav_section": "Patent", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Applicant: personal view and submission ----------------------------
    {"code": "patent.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/patent/mine",
     "required_permission": "patent.application.view_self",
     "sort_order": 5},
    {"code": "patent.submit", "label": "Submit Application",
     "icon": "Plus", "to": "/patent/submit",
     "required_permission": "patent.application.create",
     "sort_order": 10},

    # -- Director: review and decision -------------------------------------
    {"code": "patent.review", "label": "Review Applications",
     "icon": "ClipboardCheck", "to": "/patent/review",
     "required_permission": "patent.application.review",
     "sort_order": 15},

    # -- PCC_ADMIN: administration and coordination ------------------------
    {"code": "patent.admin", "label": "Administration",
     "icon": "Cog", "to": "/patent/admin",
     "required_permission": "patent.admin.manage",
     "sort_order": 25},

    # -- Attorney: legal and filing support --------------------------------
    {"code": "patent.attorney", "label": "Legal & Filing",
     "icon": "Gavel", "to": "/patent/attorney",
     "required_permission": "patent.legal.review",
     "sort_order": 30},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("patent.application.view_self", "See one's own applications"),
    ("patent.application.create", "Submit a new patent application"),
    ("patent.application.review", "Review and decide on applications"),
    ("patent.application.manage", "Manage application lifecycle (assign, withdraw, etc.)"),
    ("patent.admin.manage", "Manage PMS configuration, roles, and global settings"),
    ("patent.legal.review", "Conduct legal review, prior art search, and file patents"),
    ("patent.budget.approve", "Approve or reject patent application budgets"),
    ("patent.filing.record", "Record external patent office filings"),
    ("patent.maintenance.manage", "Manage maintenance fee renewals"),
    ("patent.appeal.review", "Review and decide on appeals"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "patent.application.auto_withdraw",  # System auto-withdrawal if deadline missed
    "patent.filing.expire",              # System filing expiry tracking
]

_STUDENT = [
    "patent.application.view_self",
    "patent.application.create",
    "patent.application.delete",
    "patent.application.withdraw",
]

_DIRECTOR = [
    "patent.application.review",
    "patent.budget.approve",
    "patent.maintenance.manage",
    "patent.appeal.review",
]

_PCC_ADMIN = [
    "patent.admin.manage",
    "patent.application.manage",
    "patent.legal.review",  # PCC_ADMIN can oversee attorney work
    "patent.budget.approve",
    "patent.filing.record",
]

_ATTORNEY = [
    "patent.legal.review",
    "patent.filing.record",
    "patent.maintenance.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Applicant": _STUDENT,
    "Director": _DIRECTOR,
    "PCC_ADMIN": _PCC_ADMIN,
    "Attorney": _ATTORNEY,
}
