"""Server-side nav for the Patent Management module (ADR-0010)."""

MODULE = {
    "code": "patent_management", "label": "Patent Management", "icon": "FaFileSignature",
    "base_path": "/patents", "nav_section": "Patents", "sort_order": 20, "status": "active",
}

NAV_ITEMS = [
    {"code": "patents.new", "label": "New Application", "icon": "FaFileSignature",
     "to": "/patents/new", "required_permission": "patent_management.application.submit",
     "sort_order": 10},
    {"code": "patents.mine", "label": "My Applications", "icon": "FaClipboardList",
     "to": "/patents/mine", "required_permission": "patent_management.application.view_own",
     "sort_order": 20},
    {"code": "patents.queue", "label": "My Assignments", "icon": "FaUserCheck",
     "to": "/patents/queue", "required_permission": "patent_management.application.view_assigned",
     "sort_order": 30},
    {"code": "patents.all", "label": "All Applications", "icon": "FaLayerGroup",
     "to": "/patents/applications", "required_permission": "patent_management.application.view_all",
     "sort_order": 40},
    {"code": "patents.reports", "label": "Reports", "icon": "FaChartBar",
     "to": "/patents/reports", "required_permission": "patent_management.report.own",
     "sort_order": 50},
    {"code": "patents.notifications", "label": "Notifications", "icon": "FaBullhorn",
     "to": "/patents/notifications", "required_permission": "patent_management.notification.view",
     "sort_order": 60},
]

PERMISSIONS = [
    ("patent_management.application.submit", "Submit a patent application"),
    ("patent_management.application.view_own", "See one's own applications"),
    ("patent_management.application.view_assigned",
     "See applications assigned as Director or Attorney"),
    ("patent_management.application.view_all", "See every application (PCC_ADMIN)"),
    ("patent_management.application.revise", "Revise and resubmit"),
    ("patent_management.application.withdraw", "Withdraw before filing"),
    ("patent_management.application.appeal", "File an appeal against a rejection"),
    ("patent_management.route.manage", "Assign Directors and Attorneys"),
    ("patent_management.review.decide", "Decide Approve, Reject or Needs Revision"),
    ("patent_management.appeal.decide", "Decide an appeal"),
    ("patent_management.attorney.respond", "Accept assignment, record opinion, budget, filing"),
    ("patent_management.budget.decide", "Approve or reject a budget"),
    ("patent_management.report.own", "See one's own application report"),
    ("patent_management.report.view", "See system-wide PMS reports"),
    ("patent_management.notification.view", "See one's own notifications"),
]

_APPLICANT = [
    "patent_management.report.own", "patent_management.notification.view",
    "patent_management.application.submit", "patent_management.application.view_own",
    "patent_management.application.revise", "patent_management.application.withdraw",
    "patent_management.application.appeal",
]
_DIRECTOR = [
    "patent_management.report.own", "patent_management.report.view",
    "patent_management.notification.view",
    "patent_management.application.view_assigned", "patent_management.review.decide",
    "patent_management.appeal.decide", "patent_management.budget.decide",
]
_ATTORNEY = [
    "patent_management.report.own", "patent_management.notification.view",
    "patent_management.application.view_assigned", "patent_management.attorney.respond",
]
_ADMIN = [
    "patent_management.report.view", "patent_management.notification.view",
    "patent_management.application.view_all", "patent_management.route.manage",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "faculty": _APPLICANT,
    "patent_director": _DIRECTOR,
    "patent_attorney": _ATTORNEY,
    "pcc_admin": _ADMIN,
}
