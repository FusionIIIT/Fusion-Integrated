"""Patent Management System module registration & permissions (ADR-0010).

Declares the navigation menu, recognized permissions, and designation grants
for the IAM and the shell.
"""

MODULE = {
    "code": "pms",
    "label": "Patent Management System",
    "icon": "Certificate",
    "base_path": "/pms",
    "nav_section": "Research & IP",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # --- Applicant Views ---
    {
        "code": "pms.applications",
        "label": "My Patents",
        "icon": "FileText",
        "to": "/pms/applications",
        "required_permission": "pms.application.view",
        "sort_order": 10,
    },
    {
        "code": "pms.new_application",
        "label": "New Submission",
        "icon": "PlusCircle",
        "to": "/pms/submit",
        "required_permission": "pms.application.create",
        "sort_order": 15,
    },
    {
        "code": "pms.prior_art",
        "label": "Prior Art Search",
        "icon": "MagnifyingGlass",
        "to": "/pms/prior-art",
        "required_permission": "pms.prior_art.view",
        "sort_order": 20,
    },
    {
        "code": "pms.my_reports",
        "label": "My Reports",
        "icon": "ChartBar",
        "to": "/pms/my-reports",
        "required_permission": "pms.report.view",
        "sort_order": 25,
    },
    # --- Director / Reviewer Views ---
    {
        "code": "pms.reviews",
        "label": "Review Queue",
        "icon": "CheckSquare",
        "to": "/pms/reviews",
        "required_permission": "pms.application.review",
        "sort_order": 30,
    },
    {
        "code": "pms.director_oversight",
        "label": "Workflow Oversight",
        "icon": "Eye",
        "to": "/pms/oversight",
        "required_permission": "pms.application.review",
        "sort_order": 35,
    },
    # --- Attorney Views ---
    {
        "code": "pms.attorney_console",
        "label": "Attorney Console",
        "icon": "Scales",
        "to": "/pms/attorney",
        "required_permission": "pms.attorney.review",
        "sort_order": 40,
    },
    {
        "code": "pms.office_actions",
        "label": "Office Actions",
        "icon": "EnvelopeSimple",
        "to": "/pms/office-actions",
        "required_permission": "pms.office_action.create",
        "sort_order": 45,
    },
    {
        "code": "pms.maintenance",
        "label": "Maintenance & Renewals",
        "icon": "ArrowsClockwise",
        "to": "/pms/maintenance",
        "required_permission": "pms.maintenance.review",
        "sort_order": 50,
    },
    # --- PCC_ADMIN Views ---
    {
        "code": "pms.admin_console",
        "label": "PCC Coordination",
        "icon": "Kanban",
        "to": "/pms/admin",
        "required_permission": "pms.application.assign",
        "sort_order": 60,
    },
    {
        "code": "pms.attorney_panels",
        "label": "Attorney Panels",
        "icon": "UsersThree",
        "to": "/pms/attorney-panels",
        "required_permission": "pms.attorney_panel.manage",
        "sort_order": 65,
    },
    {
        "code": "pms.reports",
        "label": "Portfolio Analytics",
        "icon": "PresentationChart",
        "to": "/pms/analytics",
        "required_permission": "pms.report.view",
        "sort_order": 70,
    },
    {
        "code": "pms.audit_logs",
        "label": "Compliance Audit",
        "icon": "ShieldCheck",
        "to": "/pms/audit",
        "required_permission": "pms.audit.view",
        "sort_order": 80,
    },
]

#: Every permission this module recognizes
PERMISSIONS = [
    # Application Lifecycle
    ("pms.application.view", "View patent applications within authorized scope"),
    ("pms.application.create", "Submit a new patent application"),
    ("pms.application.update", "Revise and resubmit a patent application"),
    ("pms.application.delete", "Withdraw a patent application before filing"),
    ("pms.application.assign", "Assign application to a Director for review"),
    ("pms.application.review", "Review application and record Director decision"),
    ("pms.application.expire", "System sweep to expire overdue revisions"),
    # Documents
    ("pms.document.create", "Upload supporting patent documents"),
    ("pms.document.view", "Download and inspect patent documents"),
    # Attorney Management
    ("pms.attorney.assign", "Assign attorney from panel to approved patent"),
    ("pms.attorney.review", "Assess patentability and accept/decline assignments"),
    ("pms.attorney_panel.manage", "Manage approved attorney panel and expertise"),
    # Budgeting & Filing
    ("pms.budget.review", "Review patent prosecution budget"),
    ("pms.budget.approve", "Approve patent budget for filing"),
    ("pms.filing.create", "Record external patent office filing details"),
    # Office Actions & Maintenance
    ("pms.office_action.create", "Record incoming patent office actions"),
    ("pms.office_action.review", "Review and respond to patent office actions"),
    ("pms.maintenance.review", "Manage post-grant maintenance tracking"),
    ("pms.maintenance.approve", "Decide maintenance fee renewal or abandonment"),
    # Specialized IP Operations
    ("pms.prior_art.view", "Search prior art databases"),
    ("pms.prior_art.create", "Attach prior art references to application"),
    ("pms.licensing.create", "Submit licensing or technology-transfer request"),
    ("pms.licensing.review", "Review licensing and technology-transfer requests"),
    ("pms.appeal.create", "File appeal against application rejection"),
    ("pms.appeal.review", "Review and adjudicate rejection appeal"),
    ("pms.advice.create", "Record legal and patent prosecution advice"),
    # Governance, Auditing & Configuration
    ("pms.report.view", "View patent management reports and analytics"),
    ("pms.audit.view", "Inspect immutable audit trails and compliance logs"),
    ("pms.configuration.manage", "Manage PMS system configuration and thresholds"),
    ("pms.deadline.escalate", "System sweep to escalate missed deadlines"),
]

SYSTEM_PERMISSIONS = [
    "pms.application.expire",
    "pms.deadline.escalate",
]

SCOPE_PERMISSIONS = [
    "pms.application.view",
    "pms.report.view",
]

_APPLICANT = [
    "pms.application.view",
    "pms.application.create",
    "pms.application.update",
    "pms.application.delete",
    "pms.document.create",
    "pms.document.view",
    "pms.prior_art.view",
    "pms.prior_art.create",
    "pms.office_action.review",
    "pms.licensing.create",
    "pms.appeal.create",
    "pms.report.view",
]

_DIRECTOR = [
    "pms.application.view",
    "pms.application.review",
    "pms.document.view",
    "pms.budget.review",
    "pms.budget.approve",
    "pms.maintenance.approve",
    "pms.licensing.review",
    "pms.appeal.review",
    "pms.report.view",
]

_ATTORNEY = [
    "pms.application.view",
    "pms.attorney.review",
    "pms.document.create",
    "pms.document.view",
    "pms.prior_art.view",
    "pms.prior_art.create",
    "pms.filing.create",
    "pms.office_action.create",
    "pms.office_action.review",
    "pms.maintenance.review",
    "pms.advice.create",
    "pms.report.view",
]

_PCC_ADMIN = [
    "pms.application.view",
    "pms.application.assign",
    "pms.attorney.assign",
    "pms.attorney_panel.manage",
    "pms.document.view",
    "pms.configuration.manage",
    "pms.report.view",
    "pms.audit.view",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "faculty": sorted(set(_APPLICANT + _DIRECTOR)),
    "Dean Academic": sorted(set(_DIRECTOR + _PCC_ADMIN)),
    "Director": _DIRECTOR,
    "director": _DIRECTOR,
    "acadadmin": sorted(set(_PCC_ADMIN + _ATTORNEY)),
    "staff": sorted(set(_PCC_ADMIN + _ATTORNEY)),
}
