"""RSPC module registration, navigation, permissions catalogue, and role grants.
Follows ADR-0010 and the Fusion module registry contract.
"""

from modules.rspc.permissions import PERMISSIONS, SYSTEM_PERMISSIONS

__all__ = [
    "MODULE",
    "NAV_ITEMS",
    "PERMISSIONS",
    "ROLE_GRANTS",
    "SYSTEM_PERMISSIONS",
]

MODULE = {
    "code": "rspc",
    "label": "Research & Consultancy",
    "icon": "BookOpen",
    "base_path": "/rspc",
    "nav_section": "Research",
    "sort_order": 40,
    "status": "active",
}


NAV_ITEMS = [
    {
        "code": "rspc.portfolio",
        "label": "Project Portfolio",
        "icon": "Folder",
        "to": "/rspc/portfolio",
        "required_permission": "rspc.project.view_self",
        "sort_order": 10,
    },
    {
        "code": "rspc.proposals",
        "label": "Research Proposals",
        "icon": "FileText",
        "to": "/rspc/proposals",
        "required_permission": "rspc.proposal.view_self",
        "sort_order": 20,
    },
    {
        "code": "rspc.consultancy",
        "label": "Consultancy Projects",
        "icon": "Briefcase",
        "to": "/rspc/consultancy",
        "required_permission": "rspc.consultancy.view_self",
        "sort_order": 30,
    },
    {
        "code": "rspc.approvals",
        "label": "Review & Approvals",
        "icon": "CheckSquare",
        "to": "/rspc/approvals",
        "required_permission": "rspc.proposal.view",
        "sort_order": 40,
    },
    {
        "code": "rspc.reports",
        "label": "Reports & Analytics",
        "icon": "ChartBar",
        "to": "/rspc/reports",
        "required_permission": "rspc.report.view",
        "sort_order": 50,
    },
    {
        "code": "rspc.notifications",
        "label": "Notifications",
        "icon": "Bell",
        "to": "/rspc/notifications",
        "required_permission": "rspc.notification.view_self",
        "sort_order": 60,
    },
]

# ---------------------------------------------------------------------------
# Role Grants (Keyed by designation name in globals_designation / IAM)
# ---------------------------------------------------------------------------
_FACULTY = [
    "rspc.proposal.create",
    "rspc.proposal.view_self",
    "rspc.consultancy.create",
    "rspc.consultancy.view_self",
    "rspc.project.view_self",
    "rspc.project.update",
    "rspc.staff.request",
    "rspc.staff.recommend",
    "rspc.finance.request",
    "rspc.procurement.request",
    "rspc.report.submit",
    "rspc.closure.submit",
    "rspc.notification.view_self",
]

_HOD = [
    "rspc.proposal.recommend_dept",
    "rspc.consultancy.recommend_dept",
    "rspc.proposal.view",
    "rspc.consultancy.view",
    "rspc.project.view",
    "rspc.notification.view_self",
]

_RSPC_ADMIN = [
    "rspc.proposal.view",
    "rspc.proposal.verify",
    "rspc.consultancy.view",
    "rspc.consultancy.verify",
    "rspc.project.view",
    "rspc.staff.view",
    "rspc.staff.verify",
    "rspc.finance.view",
    "rspc.finance.verify",
    "rspc.procurement.view",
    "rspc.procurement.verify",
    "rspc.report.view",
    "rspc.closure.verify",
    "rspc.audit.view",
    "rspc.integration.exchange",
    "rspc.agency.track",
    "rspc.role.sync",
    "rspc.notification.view_self",
]

_DEAN_RSPC = [
    "rspc.proposal.view",
    "rspc.proposal.approve_dean",
    "rspc.consultancy.view",
    "rspc.consultancy.approve_dean",
    "rspc.project.view",
    "rspc.staff.view",
    "rspc.staff.approve_dean",
    "rspc.finance.view",
    "rspc.finance.approve_dean",
    "rspc.procurement.view",
    "rspc.procurement.approve_dean",
    "rspc.report.view",
    "rspc.closure.approve_dean",
    "rspc.audit.view",
    "rspc.notification.view_self",
]

_DIRECTOR = [
    "rspc.proposal.view",
    "rspc.proposal.authorize_director",
    "rspc.consultancy.view",
    "rspc.consultancy.authorize_director",
    "rspc.project.view",
    "rspc.staff.view",
    "rspc.staff.authorize_director",
    "rspc.finance.view",
    "rspc.finance.authorize_director",
    "rspc.procurement.view",
    "rspc.procurement.authorize_director",
    "rspc.report.view",
    "rspc.closure.authorize_director",
    "rspc.audit.view",
    "rspc.notification.view_self",
]

ROLE_GRANTS = {
    "faculty": _FACULTY,
    "Faculty": _FACULTY,
    "hod": _HOD,
    "HoD": _HOD,
    "Head of Department": _HOD,
    "rspc_admin": _RSPC_ADMIN,
    "RSPC Admin": _RSPC_ADMIN,
    "dean_rspc": _DEAN_RSPC,
    "Dean RSPC": _DEAN_RSPC,
    "Dean-RSPC": _DEAN_RSPC,
    "director": _DIRECTOR,
    "Director": _DIRECTOR,
}
