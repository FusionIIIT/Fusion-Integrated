"""RSPC module registration, permissions, and server-driven navigation (ADR-0010)."""

MODULE = {
    "code": "rspc",
    "label": "Research & Consultancy",
    "icon": "FolderGit2",
    "base_path": "/rspc",
    "nav_section": "Research",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "rspc.proposals",
        "label": "My Proposals",
        "icon": "FileText",
        "to": "/rspc/proposals",
        "required_permission": "rspc.proposal.view",
        "sort_order": 10,
    },
    {
        "code": "rspc.projects",
        "label": "Sponsored Projects",
        "icon": "FolderGit2",
        "to": "/rspc/projects",
        "required_permission": "rspc.project.view",
        "sort_order": 20,
    },
    {
        "code": "rspc.finance",
        "label": "Financial Ledger",
        "icon": "Banknote",
        "to": "/rspc/finance",
        "required_permission": "rspc.fund.view",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    # Proposals
    ("rspc.proposal.create", "Draft and submit research proposals"),
    ("rspc.proposal.view", "View proposals and reviews"),
    ("rspc.proposal.endorse", "HoD endorsement of proposals"),
    ("rspc.proposal.approve", "Dean approval of proposals"),
    # Projects
    ("rspc.project.create", "Sanction and register research projects"),
    ("rspc.project.view", "View sponsored project records"),
    ("rspc.project.manage", "Manage project lifecycle and budget heads"),
    # Financials and Ledger
    ("rspc.fund.request", "Request fund disbursements from budget heads"),
    ("rspc.fund.view", "Inspect budget heads and financial ledger"),
    ("rspc.fund.approve", "Approve fund disbursement vouchers"),
    # Extensions and Closures
    ("rspc.extension.request", "Request project timeline extensions"),
    ("rspc.extension.approve", "Approve project timeline extensions"),
    ("rspc.closure.request", "Submit project closure and NOC requests"),
    ("rspc.closure.approve", "Approve final project closure"),
    # Reporting & Scheduled
    ("rspc.report.view", "Generate financial and utilization reports"),
    ("rspc.schedule.check_deadlines", "System check for project deadlines"),
]

SYSTEM_PERMISSIONS = [
    "rspc.schedule.check_deadlines",
]

ROLE_GRANTS = {
    "faculty": [
        "rspc.proposal.create",
        "rspc.proposal.view",
        "rspc.project.view",
        "rspc.fund.request",
        "rspc.fund.view",
        "rspc.extension.request",
        "rspc.closure.request",
    ],
    "Head of Department": [
        "rspc.proposal.view",
        "rspc.proposal.endorse",
        "rspc.project.view",
        "rspc.fund.view",
        "rspc.report.view",
    ],
    "Dean (RSPC)": [
        "rspc.proposal.view",
        "rspc.proposal.approve",
        "rspc.project.create",
        "rspc.project.view",
        "rspc.project.manage",
        "rspc.fund.view",
        "rspc.fund.approve",
        "rspc.extension.approve",
        "rspc.closure.approve",
        "rspc.report.view",
    ],
    "Director": [
        "rspc.proposal.view",
        "rspc.project.view",
        "rspc.report.view",
        "rspc.closure.approve",
    ],
    "admin": [
        "rspc.project.create",
        "rspc.project.view",
        "rspc.project.manage",
        "rspc.fund.view",
        "rspc.report.view",
    ],
}


def readiness() -> list[str]:
    """Check whether the RSPC module's prerequisites are met.

    Returns a list of unmet prerequisite descriptions. An empty list means ready.
    """
    unmet: list[str] = []
    try:
        from django.db import connection

        tables = connection.introspection.table_names()
        required_tables = [
            "rspc_proposal",
            "rspc_project",
            "rspc_project_budget_head",
            "rspc_fund_transaction",
        ]
        missing = [t for t in required_tables if t not in tables]
        if missing:
            unmet.append(f"Database tables missing (run migrations): {', '.join(missing)}")
    except Exception as exc:  # noqa: BLE001
        unmet.append(f"Database connectivity check failed: {exc}")

    try:
        from config.celery import app

        if "rspc-check-project-deadlines" not in getattr(app.conf, "beat_schedule", {}):
            unmet.append("Celery beat schedule missing 'rspc-check-project-deadlines'")
    except Exception as exc:  # noqa: BLE001
        unmet.append(f"Celery configuration check failed: {exc}")

    return unmet

