"""RSPC module registry — nav items, module metadata, role grants."""
from modules.rspc.permissions import PERMISSIONS, ROLE_GRANTS, SYSTEM_PERMISSIONS  # noqa: F401

MODULE = {
    "code": "rspc",
    "label": "RSPC",
    "icon": "FlaskConical",
    "base_path": "/rspc",
    "nav_section": "Research",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Faculty --
    {
        "code": "rspc.my_proposals",
        "label": "My Proposals",
        "icon": "FileText",
        "to": "/rspc/my-proposals",
        "required_permission": "rspc.proposal.view_self",
        "sort_order": 10,
    },
    {
        "code": "rspc.my_consultancy",
        "label": "My Consultancy",
        "icon": "Briefcase",
        "to": "/rspc/my-consultancy",
        "required_permission": "rspc.consultancy.view_self",
        "sort_order": 20,
    },
    {
        "code": "rspc.my_finance",
        "label": "My Requests",
        "icon": "CurrencyDollar",
        "to": "/rspc/my-finance",
        "required_permission": "rspc.finance.view_self",
        "sort_order": 30,
    },
    {
        "code": "rspc.my_progress_reports",
        "label": "Progress Reports",
        "icon": "ChartLine",
        "to": "/rspc/my-progress-reports",
        "required_permission": "rspc.progress_report.view_self",
        "sort_order": 40,
    },

    # -- Admin / HoD / Dean / Director --
    {
        "code": "rspc.proposals",
        "label": "Proposals",
        "icon": "Files",
        "to": "/rspc/proposals",
        "required_permission": "rspc.proposal.view",
        "sort_order": 50,
    },
    {
        "code": "rspc.consultancy",
        "label": "Consultancy",
        "icon": "Buildings",
        "to": "/rspc/consultancy",
        "required_permission": "rspc.consultancy.view",
        "sort_order": 60,
    },
    {
        "code": "rspc.appointments",
        "label": "Appointments",
        "icon": "UsersThree",
        "to": "/rspc/appointments",
        "required_permission": "rspc.appointment.view",
        "sort_order": 70,
    },
    {
        "code": "rspc.finance",
        "label": "Financial Requests",
        "icon": "Money",
        "to": "/rspc/finance",
        "required_permission": "rspc.finance.view",
        "sort_order": 80,
    },
    {
        "code": "rspc.procurement",
        "label": "Procurement",
        "icon": "Package",
        "to": "/rspc/procurement",
        "required_permission": "rspc.procurement.view",
        "sort_order": 90,
    },
    {
        "code": "rspc.progress_reports",
        "label": "Progress Reports",
        "icon": "ChartBar",
        "to": "/rspc/progress-reports",
        "required_permission": "rspc.progress_report.view",
        "sort_order": 100,
    },
    {
        "code": "rspc.closures",
        "label": "Project Closures",
        "icon": "Archive",
        "to": "/rspc/closures",
        "required_permission": "rspc.closure.view",
        "sort_order": 110,
    },
    {
        "code": "rspc.reports",
        "label": "Reports",
        "icon": "PresentationChart",
        "to": "/rspc/reports",
        "required_permission": "rspc.report.view",
        "sort_order": 120,
    },
]
