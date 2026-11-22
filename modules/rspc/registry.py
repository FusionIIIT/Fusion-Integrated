"""RSPC module registry descriptor (ADR-0010).

Defines module metadata, permissions catalog, navigation items, and role grants for the IAM.
"""
MODULE = {
    "code": "rspc",
    "label": "Research, Sponsored Projects & Consultancy",
    "icon": "FolderSimpleLock",
    "base_path": "/rspc",
    "nav_section": "Research",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "rspc.proposals",
        "label": "Research Proposals",
        "icon": "FolderSimpleLock",
        "to": "/rspc/proposals",
        "required_permission": "rspc.proposal.view",
        "sort_order": 10,
    },
    {
        "code": "rspc.consultancy",
        "label": "Consultancy Projects",
        "icon": "Briefcase",
        "to": "/rspc/consultancy",
        "required_permission": "rspc.consultancy.view",
        "sort_order": 20,
    },
    {
        "code": "rspc.financial",
        "label": "Fund Requests",
        "icon": "Coins",
        "to": "/rspc/financial",
        "required_permission": "rspc.financial.request",
        "sort_order": 30,
    },
    {
        "code": "rspc.reports",
        "label": "Progress & Closure Reports",
        "icon": "ChartBar",
        "to": "/rspc/reports",
        "required_permission": "rspc.report.submit",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("rspc.proposal.view", "View research proposals"),
    ("rspc.proposal.submit", "Submit research proposals"),
    ("rspc.proposal.recommend_hod", "HoD review and recommend research proposals"),
    ("rspc.proposal.verify_admin", "RSPC Admin verify research proposals"),
    ("rspc.proposal.approve_dean", "Dean RSPC approve research proposals"),
    ("rspc.proposal.authorize_director", "Director authorize high-value proposals"),
    ("rspc.consultancy.view", "View consultancy projects"),
    ("rspc.consultancy.register", "Register consultancy projects"),
    ("rspc.consultancy.recommend_hod", "HoD recommend consultancy projects"),
    ("rspc.consultancy.approve_dean", "Dean RSPC approve consultancy projects"),
    ("rspc.staff.request", "Request project staff appointment"),
    ("rspc.staff.manage", "Manage and verify project staff appointments"),
    ("rspc.financial.request", "Submit fund utilization and expenditure request"),
    ("rspc.financial.verify", "Verify financial requests"),
    ("rspc.financial.approve_dean", "Approve financial requests within delegated powers"),
    ("rspc.financial.authorize_director", "Authorize high-value expenditure requests"),
    ("rspc.procurement.request", "Request project equipment or consumable procurement"),
    ("rspc.procurement.approve", "Approve project procurement requests"),
    ("rspc.report.submit", "Submit periodic progress and utilization reports"),
    ("rspc.closure.submit", "Submit project closure request"),
    ("rspc.closure.approve", "Approve project closure and archival"),
    ("rspc.audit.view", "View RSPC audit trails and compliance records"),
]

SYSTEM_PERMISSIONS = []

_FACULTY = [
    "rspc.proposal.view",
    "rspc.proposal.submit",
    "rspc.consultancy.view",
    "rspc.consultancy.register",
    "rspc.staff.request",
    "rspc.financial.request",
    "rspc.procurement.request",
    "rspc.report.submit",
    "rspc.closure.submit",
]

_HOD = [
    *_FACULTY,
    "rspc.proposal.recommend_hod",
    "rspc.consultancy.recommend_hod",
]

_ADMIN = [
    "rspc.proposal.view",
    "rspc.proposal.verify_admin",
    "rspc.consultancy.view",
    "rspc.staff.manage",
    "rspc.financial.verify",
    "rspc.procurement.request",
    "rspc.report.submit",
    "rspc.closure.approve",
    "rspc.audit.view",
]

_DEAN = [
    *_ADMIN,
    "rspc.proposal.approve_dean",
    "rspc.consultancy.approve_dean",
    "rspc.financial.approve_dean",
    "rspc.procurement.approve",
]

_DIRECTOR = [
    *_DEAN,
    "rspc.proposal.authorize_director",
    "rspc.financial.authorize_director",
]

ROLE_GRANTS = {
    "faculty": _FACULTY,
    "hod": _HOD,
    "rspc_admin": _ADMIN,
    "dean_rspc": _DEAN,
    "director": _DIRECTOR,
}
