MODULE = {
    "code": "hreis",
    "label": "Human Resources",
    "icon": "FaUsers",
    "base_path": "/hreis",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "hreis.records",
        "label": "Service Records",
        "icon": "FaIdCard",
        "to": "/hreis/records",
        "required_permission": "hreis.record.view_self",
        "sort_order": 10,
    },
    {
        "code": "hreis.leave",
        "label": "Leave Requests",
        "icon": "FaCalendarAlt",
        "to": "/hreis/leave",
        "required_permission": "hreis.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "hreis.appraisals",
        "label": "Appraisals",
        "icon": "FaFileAlt",
        "to": "/hreis/appraisals",
        "required_permission": "hreis.appraisal.submit",
        "sort_order": 30,
    },
    {
        "code": "hreis.claims",
        "label": "LTC and CPDA",
        "icon": "FaMoneyBill",
        "to": "/hreis/claims",
        "required_permission": "hreis.claim.submit",
        "sort_order": 40,
    },
    {
        "code": "hreis.approvals",
        "label": "Approvals",
        "icon": "FaTasks",
        "to": "/hreis/approvals",
        "required_permission": "hreis.leave.review",
        "sort_order": 50,
    },
    {
        "code": "hreis.admin",
        "label": "HR Administration",
        "icon": "FaCog",
        "to": "/hreis/admin",
        "required_permission": "hreis.workflow.configure",
        "sort_order": 60,
    },
    {
        "code": "hreis.finance",
        "label": "Claim Settlements",
        "icon": "FaMoneyBill",
        "to": "/hreis/approvals",
        "required_permission": "hreis.claim.process",
        "sort_order": 55,
    },
    {
        "code": "hreis.notifications",
        "label": "Notifications",
        "icon": "FaBell",
        "to": "/hreis/notifications",
        "required_permission": "hreis.notification.view",
        "sort_order": 65,
    },
    {
        "code": "hreis.audit",
        "label": "HR Audit",
        "icon": "FaHistory",
        "to": "/hreis/audit",
        "required_permission": "hreis.audit.view",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("hreis.record.view_self", "View own service record"),
    ("hreis.record.manage", "Maintain service records"),
    ("hreis.leave.apply", "Apply for leave and track applications"),
    ("hreis.leave.review", "Decide routed leave requests"),
    ("hreis.appraisal.submit", "Submit annual appraisals"),
    ("hreis.appraisal.assign", "Assign appraisal reviewers"),
    ("hreis.appraisal.review", "Review and finalize assigned appraisals"),
    ("hreis.claim.submit", "Submit LTC and CPDA claims"),
    ("hreis.claim.verify", "Verify claims and eligibility"),
    ("hreis.claim.review", "Decide routed claims"),
    ("hreis.claim.process", "Record approved claim settlement status"),
    ("hreis.workflow.configure", "Configure HR workflows and appraisal windows"),
    ("hreis.audit.view", "Review immutable HR audit records"),
    ("hreis.notification.view", "View own HR notifications"),
    ("hreis.notification.manage", "Create policy and deadline notifications"),
]

_EMPLOYEE = [
    "hreis.record.view_self",
    "hreis.leave.apply",
    "hreis.appraisal.submit",
    "hreis.claim.submit",
    "hreis.notification.view",
]
_AUTHORITY = ["hreis.leave.review", "hreis.claim.review", "hreis.appraisal.review"]
_HR = [
    "hreis.record.manage",
    "hreis.appraisal.assign",
    "hreis.claim.verify",
    "hreis.workflow.configure",
    "hreis.audit.view",
    "hreis.notification.manage",
]
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "HOD": _AUTHORITY,
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "HR Administrator": [*_EMPLOYEE, *_HR, "hreis.leave.review"],
    "Accountant": ["hreis.claim.process"],
}
