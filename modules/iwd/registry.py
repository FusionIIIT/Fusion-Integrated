"""What the server tells the shell about the IWD module (ADR-0010, BR-IWD-001).

Derived from authoritative requirements:
- CFR-IWD-01..16
- AFR-IWD-001..060
- BR-IWD-001, BR-IWD-018
- Use cases UC-IWD-001..151
"""

MODULE = {
    "code": "iwd",
    "label": "Institute Works Department",
    "icon": "Wrench",
    "base_path": "/iwd",
    "nav_section": "Campus",
    "sort_order": 20,
    "status": "planned",
}

#: Client routes will be implemented in the frontend phase.
#: Empty for now to satisfy ops/checks/nav_matches_routes.py.
NAV_ITEMS = []

PERMISSIONS = [
    # -- 1. Complainant (Institute Employee) -----------------------------------
    ("iwd.complaint.create", "Submit a maintenance complaint"),
    ("iwd.complaint.view_self", "View own submitted maintenance complaints"),
    ("iwd.complaint.view", "View maintenance complaints within authorized scope"),
    ("iwd.feedback.create", "Submit feedback and rating for resolved maintenance work"),
    ("iwd.feedback.view", "View recorded maintenance feedback and ratings"),

    # -- 2. Engineer -----------------------------------------------------------
    ("iwd.complaint.assess", "Assess assigned complaint and prepare repair estimate"),
    ("iwd.work.execute", "Record work execution progress and mark repair work complete"),
    ("iwd.bill.create", "Submit final bill and supporting records after physical verification"),
    ("iwd.urgent.flag", "Flag active repair work as urgent for fast-track attention"),

    # -- 3. IWD Admin ----------------------------------------------------------
    ("iwd.estimate.review_low", "Review, approve, or reject low-cost estimates (< Rs.25k)"),
    ("iwd.inventory.manage", "Manage inventory stock, issue materials, and coordinate shortage procurement"),
    ("iwd.bidding.manage", "Conduct external competitive bidding and vendor selection"),

    # -- 4. Review Committee & Department Head ---------------------------------
    ("iwd.estimate.review_committee", "Record necessity and feasibility recommendation for mid-range estimates"),
    ("iwd.estimate.review_mid", "Review, approve, reject, or forward mid-range estimates (Rs.25k-2.5L)"),
    ("iwd.work.verify", "Conduct physical quality verification of completed work"),
    ("iwd.urgent.review", "Review urgent fast-track escalation"),

    # -- 5. Director -----------------------------------------------------------
    ("iwd.estimate.review_director", "Review and approve high-cost bidding (> Rs.2.5L) or forwarded estimates"),
    ("iwd.payment.approve", "Grant final approval for payment settlement after Auditor validation"),

    # -- 6. Auditor & Accounts Department --------------------------------------
    ("iwd.bill.audit", "Audit and validate final bill against approved estimate and work evidence"),
    ("iwd.payment.settle", "Record and execute payment settlement"),

    # -- 7. System operations --------------------------------------------------
    ("iwd.complaint.auto_assign", "System automatic assignment of complaint"),
]

#: System permissions performed by automated tasks / service logic.
SYSTEM_PERMISSIONS = [
    "iwd.complaint.auto_assign",
]

#: Scoped permissions: holding it widens visibility rather than granting a write action.
SCOPE_PERMISSIONS = [
    "iwd.complaint.view",
]

# -- Designation Grants --------------------------------------------------------
_EMPLOYEE = [
    "iwd.complaint.create",
    "iwd.complaint.view_self",
    "iwd.feedback.create",
]

_ENGINEER = [
    *_EMPLOYEE,
    "iwd.complaint.view",
    "iwd.complaint.assess",
    "iwd.work.execute",
    "iwd.bill.create",
    "iwd.urgent.flag",
]

_IWD_ADMIN = [
    *_EMPLOYEE,
    "iwd.complaint.view",
    "iwd.estimate.review_low",
    "iwd.inventory.manage",
    "iwd.bidding.manage",
    "iwd.feedback.view",
]

_DEPT_HEAD = [
    *_EMPLOYEE,
    "iwd.complaint.view",
    "iwd.estimate.review_committee",
    "iwd.estimate.review_mid",
    "iwd.work.verify",
    "iwd.urgent.review",
    "iwd.feedback.view",
]

_DEAN = [
    *_EMPLOYEE,
    "iwd.complaint.view",
    "iwd.feedback.view",
]

_DIRECTOR = [
    *_EMPLOYEE,
    "iwd.complaint.view",
    "iwd.estimate.review_director",
    "iwd.payment.approve",
    "iwd.urgent.review",
    "iwd.feedback.view",
]

_AUDITOR = [
    "iwd.complaint.view",
    "iwd.bill.audit",
]

_ACCOUNTS = [
    "iwd.complaint.view",
    "iwd.payment.settle",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "iwd_engineer": _ENGINEER,
    "iwd_admin": _IWD_ADMIN,
    "Department Head": _DEPT_HEAD,
    "Dean": _DEAN,
    "Director": _DIRECTOR,
    "auditor": _AUDITOR,
    "accounts_officer": _ACCOUNTS,
}

