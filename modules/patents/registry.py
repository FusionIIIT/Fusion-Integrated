"""What the server tells the shell about the patents module (ADR-0010)."""

MODULE = {
    "code": "patents",
    "label": "Patent Management",
    "icon": "Certificate",
    "base_path": "/patents",
    "nav_section": "Research",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- applicant (faculty, student, staff) ---------------------------------
    {
        "code": "patents.mine",
        "label": "My Applications",
        "icon": "Files",
        "to": "/patents/mine",
        "required_permission": "patents.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "patents.new",
        "label": "New Application",
        "icon": "FilePlus",
        "to": "/patents/new",
        "required_permission": "patents.application.create",
        "sort_order": 20,
    },
    {
        "code": "patents.prior_art",
        "label": "Prior Art Search",
        "icon": "MagnifyingGlass",
        "to": "/patents/prior-art",
        "required_permission": "patents.prior_art.search",
        "sort_order": 30,
    },

    # -- director (evaluator & authority) ------------------------------------
    {
        "code": "patents.director_reviews",
        "label": "Review Queue",
        "icon": "ClipboardText",
        "to": "/patents/reviews",
        "required_permission": "patents.application.review",
        "sort_order": 40,
    },
    {
        "code": "patents.director_budgets",
        "label": "Budget Approvals",
        "icon": "CurrencyInr",
        "to": "/patents/budget-approvals",
        "required_permission": "patents.budget.approve",
        "sort_order": 50,
    },
    {
        "code": "patents.director_renewals",
        "label": "Maintenance Renewals",
        "icon": "ClockCounterClockwise",
        "to": "/patents/maintenance-decisions",
        "required_permission": "patents.maintenance.decide",
        "sort_order": 55,
    },

    # -- attorney ------------------------------------------------------------
    {
        "code": "patents.attorney_assignments",
        "label": "Attorney Docket",
        "icon": "Briefcase",
        "to": "/patents/docket",
        "required_permission": "patents.assessment.perform",
        "sort_order": 60,
    },
    {
        "code": "patents.office_actions",
        "label": "Office Actions",
        "icon": "WarningCircle",
        "to": "/patents/office-actions",
        "required_permission": "patents.office_action.respond",
        "sort_order": 70,
    },

    # -- coordinator / admin -------------------------------------------------
    {
        "code": "patents.admin_queue",
        "label": "All Applications",
        "icon": "Folders",
        "to": "/patents/all",
        "required_permission": "patents.application.view",
        "sort_order": 80,
    },
    {
        "code": "patents.attorney_panel",
        "label": "Attorney Panel",
        "icon": "Scales",
        "to": "/patents/attorney-panel",
        "required_permission": "patents.panel.manage",
        "sort_order": 90,
    },
    {
        "code": "patents.reports",
        "label": "Reports & Analytics",
        "icon": "ChartBar",
        "to": "/patents/reports",
        "required_permission": "patents.report.view",
        "sort_order": 100,
    },
]

PERMISSIONS = [
    # Application lifecycle
    ("patents.application.create", "Submit a new patent application"),
    ("patents.application.view_self", "View one's own patent applications and reports"),
    ("patents.application.view", "View patent applications within authorized scope"),
    ("patents.application.update", "Revise and update an application"),
    ("patents.application.withdraw", "Withdraw an application before filing"),
    ("patents.application.assign_director", "Assign submitted application to Director"),
    ("patents.application.review", "Review technical merit and decide application"),
    ("patents.application.appeal", "File an appeal against a rejection"),
    ("patents.application.decide_appeal", "Adjudicate an appeal"),

    # Attorney & Assessment
    ("patents.attorney.assign", "Assign attorney to approved application"),
    ("patents.attorney.respond_assignment", "Accept or decline attorney assignment"),
    ("patents.assessment.perform", "Conduct patentability and prior-art assessment"),
    ("patents.filing.record", "Record external patent office filing details"),
    ("patents.office_action.record", "Record external office actions"),
    ("patents.office_action.respond", "Prepare and submit office action responses"),
    ("patents.office_action.approve", "Review and approve office action response"),

    # Budget & Financial
    ("patents.budget.approve", "Review and approve patent filing and prosecution budgets"),
    ("patents.budget.view", "View patent budget and expenditure records"),

    # Post-grant Maintenance
    ("patents.maintenance.track", "Track post-grant maintenance schedules and fees"),
    ("patents.maintenance.decide", "Make patent maintenance renewal decisions"),

    # Technology Transfer & Prior Art
    ("patents.tech_transfer.create", "Submit technology transfer or licensing request"),
    ("patents.tech_transfer.review", "Review technology transfer agreements"),
    ("patents.prior_art.search", "Search and attach prior-art references"),

    # Administration & Oversight
    ("patents.panel.manage", "Manage attorney panel roster and expertise mappings"),
    ("patents.workflow.handle_exceptions", "Handle and route escalated and exceptional cases"),
    ("patents.audit.view", "View audit trail and compliance logs"),
    ("patents.report.view", "Generate and view reports and analytics"),

    # System permissions
    ("patents.application.expire", "System revision expiration"),
    ("patents.maintenance.sweep", "System maintenance deadline sweep"),
]

SYSTEM_PERMISSIONS = [
    "patents.application.expire",
    "patents.maintenance.sweep",
]

SCOPE_PERMISSIONS = [
    "patents.application.view",
    "patents.application.review",
    "patents.report.view",
]

_APPLICANT = [
    "patents.application.create",
    "patents.application.view_self",
    "patents.application.update",
    "patents.application.withdraw",
    "patents.application.appeal",
    "patents.prior_art.search",
    "patents.office_action.approve",
    "patents.tech_transfer.create",
]

_DIRECTOR = [
    "patents.application.view",
    "patents.application.review",
    "patents.application.decide_appeal",
    "patents.budget.approve",
    "patents.budget.view",
    "patents.maintenance.decide",
    "patents.tech_transfer.review",
    "patents.report.view",
]

_ATTORNEY = [
    "patents.application.view",
    "patents.attorney.respond_assignment",
    "patents.assessment.perform",
    "patents.filing.record",
    "patents.office_action.record",
    "patents.office_action.respond",
    "patents.maintenance.track",
    "patents.prior_art.search",
]

_PCC_ADMIN = [
    "patents.application.view",
    "patents.workflow.handle_exceptions",
    "patents.application.assign_director",
    "patents.attorney.assign",
    "patents.panel.manage",
    "patents.budget.view",
    "patents.report.view",
    "patents.audit.view",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "Director": _DIRECTOR,
    "attorney": _ATTORNEY,
    "pcc_admin": _PCC_ADMIN,
}


def readiness() -> list[str]:
    """Returns unmet deployment prerequisites for the patents module (Step 7.5, ADR-0010)."""
    unmet: list[str] = []
    try:
        from django.db import DatabaseError

        from modules.patents.models.policy import PatentPolicy

        if not PatentPolicy.objects.filter(is_active=True).exists():
            unmet.append("Patent policy is not seeded — run 'manage.py pms_seed_policy'")
    except DatabaseError:
        unmet.append("Database tables are not migrated — run 'manage.py migrate'")
    return unmet

