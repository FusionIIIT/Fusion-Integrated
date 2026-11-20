"""PMS Registry declarations (ADR-0010)."""

from .permissions import PERMISSIONS  # noqa: F401 — consumed by permission_manifest

MODULE = {
    "code": "pms",
    "label": "Patent Management",
    "icon": "FileText",
    "base_path": "/pms",
    "nav_section": "Research",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "pms.mine",
        "label": "My Applications",
        "icon": "FileText",
        "to": "/pms/mine",
        "required_permission": "pms.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "pms.submit",
        "label": "New Application",
        "icon": "PlusCircle",
        "to": "/pms/submit",
        "required_permission": "pms.application.create",
        "sort_order": 15,
    },
    {
        "code": "pms.queue",
        "label": "Application Queue",
        "icon": "Inbox",
        "to": "/pms/queue",
        "required_permission": "pms.application.view",
        "sort_order": 20,
    },
    {
        "code": "pms.reviews",
        "label": "Director Reviews",
        "icon": "CheckSquare",
        "to": "/pms/reviews",
        "required_permission": "pms.application.review",
        "sort_order": 30,
    },
    {
        "code": "pms.filings",
        "label": "Patent Filings",
        "icon": "Send",
        "to": "/pms/filings",
        "required_permission": "pms.filing.record",
        "sort_order": 40,
    },
    {
        "code": "pms.maintenance",
        "label": "Maintenance",
        "icon": "Clock",
        "to": "/pms/maintenance",
        "required_permission": "pms.maintenance.manage",
        "sort_order": 50,
    },
    {
        "code": "pms.reports",
        "label": "Reports",
        "icon": "ChartBar",
        "to": "/pms/reports",
        "required_permission": "pms.report.view",
        "sort_order": 60,
    },
    {
        "code": "pms.my_reports",
        "label": "My Reports",
        "icon": "ChartPie",
        "to": "/pms/my-reports",
        "required_permission": "pms.report.view_self",
        "sort_order": 65,
    },
    {
        "code": "pms.admin",
        "label": "Administration",
        "icon": "Gear",
        "to": "/pms/admin",
        "required_permission": "pms.config.manage",
        "sort_order": 70,
    },
    {
        "code": "pms.audit",
        "label": "Audit Trail",
        "icon": "ShieldCheck",
        "to": "/pms/audit",
        "required_permission": "pms.audit.view",
        "sort_order": 80,
    },
]

SYSTEM_PERMISSIONS = [
    "pms.application.auto_expire",
    "pms.deadline.escalate",
]

_APPLICANT = [
    "pms.application.create",
    "pms.application.view_self",
    "pms.application.withdraw",
    "pms.application.revise",
    "pms.application.appeal",
    "pms.office_action.review",
    "pms.prior_art.search",
    "pms.document.manage",
    "pms.licensing.submit",
    "pms.coinventor.manage",
    "pms.report.view_self",
]

_DIRECTOR = [
    "pms.application.view",
    "pms.application.review",
    "pms.application.review_appeal",
    "pms.budget.review",
    "pms.maintenance.decide",
    "pms.licensing.review",
    "pms.workflow.oversight",
    "pms.report.view",
    "pms.audit.view",
    "pms.document.manage",
]

_ATTORNEY = [
    "pms.application.view",
    "pms.attorney.respond_assignment",
    "pms.patentability.assess",
    "pms.filing.record",
    "pms.office_action.record",
    "pms.office_action.respond",
    "pms.maintenance.manage",
    "pms.prior_art.search",
    "pms.advice.record",
    "pms.document.manage",
]

_PCC_ADMIN = [
    "pms.application.view",
    "pms.application.assign_director",
    "pms.attorney.assign",
    "pms.workflow.monitor",
    "pms.report.view",
    "pms.config.manage",
    "pms.panel.manage",
    "pms.audit.view",
    "pms.document.manage",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "director": _DIRECTOR,
    "attorney": _ATTORNEY,
    "pcc_admin": _PCC_ADMIN,
    "Dean Research": _DIRECTOR,
}
