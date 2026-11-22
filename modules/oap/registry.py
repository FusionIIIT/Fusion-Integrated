"""Server-driven navigation and permissions for Other Academic Procedures (ADR-0010)."""

MODULE = {
    "code": "oap",
    "label": "Other Academic Procedures",
    "icon": "GraduationCap",
    "base_path": "/oap",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student Views --
    {
        "code": "oap.dashboard",
        "label": "OAP Overview",
        "icon": "SquaresFour",
        "to": "/oap",
        "required_permission": "oap.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "oap.leave",
        "label": "Student Leave",
        "icon": "CalendarBlank",
        "to": "/oap/leave",
        "required_permission": "oap.leave.create",
        "sort_order": 20,
    },
    {
        "code": "oap.bonafide",
        "label": "Bonafide Certificate",
        "icon": "Certificate",
        "to": "/oap/bonafide",
        "required_permission": "oap.bonafide.create",
        "sort_order": 30,
    },
    {
        "code": "oap.nodues",
        "label": "No-Dues Clearance",
        "icon": "CheckSquare",
        "to": "/oap/no-dues",
        "required_permission": "oap.nodues.view",
        "sort_order": 40,
    },
    {
        "code": "oap.branch_change",
        "label": "Branch Change",
        "icon": "Shuffle",
        "to": "/oap/branch-change",
        "required_permission": "oap.branchchange.apply",
        "sort_order": 50,
    },
    # -- Approver / Staff Views --
    {
        "code": "oap.approvals",
        "label": "Approval Queue",
        "icon": "UserCheck",
        "to": "/oap/approvals",
        "required_permission": "oap.leave.approve",
        "sort_order": 60,
    },
    {
        "code": "oap.admin_bonafide",
        "label": "Issue Bonafide",
        "icon": "Stamp",
        "to": "/oap/admin/bonafide",
        "required_permission": "oap.bonafide.issue",
        "sort_order": 70,
    },
    {
        "code": "oap.admin_nodues",
        "label": "No-Dues Registry",
        "icon": "ClipboardText",
        "to": "/oap/admin/no-dues",
        "required_permission": "oap.nodues.finalize",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("oap.request.view_self", "View one's own academic procedure requests"),
    ("oap.leave.create", "Submit student leave application"),
    ("oap.leave.view_self", "View personal leave applications"),
    ("oap.leave.recommend", "Recommend leave as faculty advisor or supervisor"),
    ("oap.leave.approve", "Approve or reject leave application as HoD"),
    ("oap.bonafide.create", "Apply for bonafide certificate"),
    ("oap.bonafide.view_self", "View personal bonafide certificate requests"),
    ("oap.bonafide.issue", "Verify and issue bonafide certificate"),
    ("oap.nodues.view", "View no-dues clearance status"),
    ("oap.nodues.initiate", "Initiate no-dues clearance process"),
    ("oap.nodues.signoff", "Record departmental dues sign-off"),
    ("oap.nodues.finalize", "Finalize and issue consolidated no-dues certificate"),
    ("oap.branchchange.apply", "Submit branch change application"),
    ("oap.branchchange.manage", "Validate eligibility and allocate branch change seats"),
    ("oap.branchchange.approve", "Sanction final branch change decisions"),
]

_STUDENT = [
    "oap.request.view_self",
    "oap.leave.create",
    "oap.leave.view_self",
    "oap.bonafide.create",
    "oap.bonafide.view_self",
    "oap.nodues.view",
    "oap.nodues.initiate",
    "oap.branchchange.apply",
]

_FACULTY = [
    "oap.leave.recommend",
]

_HOD = [
    "oap.leave.approve",
    "oap.nodues.signoff",
]

_ACADEMIC_ADMIN = [
    "oap.bonafide.issue",
    "oap.nodues.finalize",
    "oap.branchchange.manage",
]

_DEAN_ACADEMICS = [
    "oap.leave.approve",
    "oap.branchchange.approve",
    "oap.nodues.finalize",
]

_CUSTODIAN = [
    "oap.nodues.signoff",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "hod": _HOD,
    "academic_admin": _ACADEMIC_ADMIN,
    "Dean Academic": _DEAN_ACADEMICS,
    "custodian": _CUSTODIAN,
}
