"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "pms",
    "label": "Patent Management",
    "icon": "Certificate",
    "base_path": "/pms",
    "nav_section": "Research & IPR",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- applicant view ---
    {
        "code": "pms.dashboard",
        "label": "Dashboard",
        "icon": "Gauge",
        "to": "/pms",
        "required_permission": "pms.application.view_self",
        "sort_order": 5,
    },
    {
        "code": "pms.new_application",
        "label": "New Application",
        "icon": "PlusCircle",
        "to": "/pms/applications/new",
        "required_permission": "pms.application.create",
        "sort_order": 10,
    },
    {
        "code": "pms.reviews",
        "label": "Scrutiny & Reviews",
        "icon": "ClipboardCheck",
        "to": "/pms/reviews",
        "required_permission": "pms.review.view_assigned",
        "sort_order": 20,
    },
    {
        "code": "pms.office_actions",
        "label": "Office Actions & FER",
        "icon": "FileText",
        "to": "/pms/office-actions",
        "required_permission": "pms.office_action.manage",
        "sort_order": 30,
    },
    {
        "code": "pms.maintenance",
        "label": "Annuity & Renewals",
        "icon": "ClockCounterClockwise",
        "to": "/pms/maintenance",
        "required_permission": "pms.maintenance.manage",
        "sort_order": 40,
    },
    {
        "code": "pms.finance",
        "label": "Financial Ledger",
        "icon": "Receipt",
        "to": "/pms/finance",
        "required_permission": "pms.config.manage",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    # Applicant capabilities
    {"code": "pms.application.create", "label": "Create and edit patent draft"},
    {"code": "pms.application.view_self", "label": "View own patent applications"},
    {"code": "pms.application.submit", "label": "Submit patent application for review"},
    {"code": "pms.application.withdraw", "label": "Withdraw patent application"},
    {"code": "pms.agreement.sign", "label": "Sign co-inventor agreement"},
    {"code": "pms.appeal.create", "label": "File appeal against application rejection"},

    # Reviewer & Director capabilities
    {"code": "pms.review.view_assigned", "label": "View assigned applications for review"},
    {"code": "pms.review.submit", "label": "Submit technical review and recommendation"},
    {"code": "pms.application.decide", "label": "Approve or reject patent application"},
    {"code": "pms.budget.decide", "label": "Approve, reject, or escalate patent budget"},

    # Attorney capabilities
    {"code": "pms.attorney.respond", "label": "Accept or decline attorney assignment"},
    {"code": "pms.filing.record", "label": "Record external patent office filing details"},
    {"code": "pms.office_action.manage", "label": "Log and respond to patent office actions"},
    {"code": "pms.advice.create", "label": "Record patent legal advice"},

    # Coordinator / Admin capabilities
    {"code": "pms.application.view", "label": "View all institute patent applications"},
    {"code": "pms.director.assign", "label": "Assign director / scrutiny reviewer"},
    {"code": "pms.attorney.assign", "label": "Assign attorney from empanelled roster"},
    {"code": "pms.maintenance.manage", "label": "Manage annuity maintenance and renewals"},
    {"code": "pms.report.view", "label": "View PMS system-wide reports and analytics"},
    {"code": "pms.config.manage", "label": "Manage PMS policy, attorney panels, and roles"},
]

SYSTEM_PERMISSIONS = [
    "pms.schedule.expire_deadlines",
    "pms.schedule.sync_maintenance",
]

ROLE_GRANTS = {
    "student": [
        "pms.application.create",
        "pms.application.view_self",
        "pms.application.submit",
        "pms.application.withdraw",
        "pms.agreement.sign",
        "pms.appeal.create",
    ],
    "faculty": [
        "pms.application.create",
        "pms.application.view_self",
        "pms.application.submit",
        "pms.application.withdraw",
        "pms.agreement.sign",
        "pms.appeal.create",
        "pms.review.view_assigned",
        "pms.review.submit",
    ],
    "staff": [
        "pms.application.create",
        "pms.application.view_self",
        "pms.application.submit",
        "pms.agreement.sign",
    ],
    "Dean R&D": [
        "pms.application.view",
        "pms.application.decide",
        "pms.director.assign",
        "pms.budget.decide",
        "pms.attorney.assign",
        "pms.report.view",
    ],
    "Director": [
        "pms.application.view",
        "pms.application.decide",
        "pms.budget.decide",
        "pms.report.view",
    ],
    "pcc_admin": [
        "pms.application.view",
        "pms.director.assign",
        "pms.attorney.assign",
        "pms.maintenance.manage",
        "pms.report.view",
        "pms.config.manage",
    ],
    "pms_attorney": [
        "pms.attorney.respond",
        "pms.filing.record",
        "pms.office_action.manage",
        "pms.advice.create",
    ],
}
