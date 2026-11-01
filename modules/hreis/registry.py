"""HR-EIS Server-driven Navigation & Permission Registry (ADR-0010)."""

MODULE = {
    "code": "hr_eis",
    "label": "Human Resources",
    "icon": "Users",
    "base_path": "/hr",
    "nav_section": "Administration",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee self-service --
    {
        "code": "hreis.overview",
        "label": "HR Overview",
        "icon": "Gauge",
        "to": "/hr/overview",
        "required_permission": "hr_eis.service_record.view_self",
        "sort_order": 5,
    },
    {
        "code": "hreis.service_record",
        "label": "My Service Record",
        "icon": "IdCard",
        "to": "/hr/service-record",
        "required_permission": "hr_eis.service_record.view_self",
        "sort_order": 10,
    },
    {
        "code": "hreis.leaves",
        "label": "Leave Management",
        "icon": "CalendarTime",
        "to": "/hr/leaves",
        "required_permission": "hr_eis.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "hreis.appraisals",
        "label": "Annual Appraisals",
        "icon": "FileCertificate",
        "to": "/hr/appraisals",
        "required_permission": "hr_eis.appraisal.submit",
        "sort_order": 30,
    },
    {
        "code": "hreis.ltc",
        "label": "LTC Claims",
        "icon": "PlaneDeparture",
        "to": "/hr/ltc",
        "required_permission": "hr_eis.ltc.apply",
        "sort_order": 40,
    },
    {
        "code": "hreis.cpda",
        "label": "CPDA Allowance",
        "icon": "Coins",
        "to": "/hr/cpda",
        "required_permission": "hr_eis.cpda.apply",
        "sort_order": 50,
    },
    # -- Approving Authority --
    {
        "code": "hreis.approvals",
        "label": "Pending Approvals",
        "icon": "Checks",
        "to": "/hr/approvals",
        "required_permission": "hr_eis.leave.review",
        "sort_order": 60,
    },
    # -- HR Administrator --
    {
        "code": "hreis.verification",
        "label": "HR Verification",
        "icon": "FileCheck",
        "to": "/hr/verification",
        "required_permission": "hr_eis.ltc.verify",
        "sort_order": 70,
    },
    {
        "code": "hreis.appraisal_admin",
        "label": "Appraisal Reviewers",
        "icon": "UserCheck",
        "to": "/hr/appraisal-admin",
        "required_permission": "hr_eis.appraisal.assign_reviewer",
        "sort_order": 75,
    },
    {
        "code": "hreis.admin_settings",
        "label": "HR Administration",
        "icon": "Settings",
        "to": "/hr/admin",
        "required_permission": "hr_eis.service_record.manage",
        "sort_order": 80,
    },
    {
        "code": "hreis.audit",
        "label": "Audit & Compliance",
        "icon": "ShieldCheck",
        "to": "/hr/audit",
        "required_permission": "hr_eis.audit.view",
        "sort_order": 85,
    },
    # -- Accountant --
    {
        "code": "hreis.settlement",
        "label": "Claim Settlements",
        "icon": "Receipt",
        "to": "/hr/settlement",
        "required_permission": "hr_eis.ltc.settle",
        "sort_order": 90,
    },
]

PERMISSIONS = [
    ("hr_eis.service_record.view_self", "View own employee service record"),
    ("hr_eis.service_record.manage", "Create and update employee service records"),
    ("hr_eis.service_record.view_all", "View all employee service records"),
    ("hr_eis.leave.apply", "Submit leave requests"),
    ("hr_eis.leave.view_self", "View own leave requests"),
    ("hr_eis.leave.review", "Review, approve, reject, or forward leave requests"),
    ("hr_eis.appraisal.submit", "Submit annual appraisal form"),
    ("hr_eis.appraisal.view_self", "View own appraisal submissions"),
    ("hr_eis.appraisal.assign_reviewer", "Assign reviewers to annual appraisals"),
    ("hr_eis.appraisal.review", "Review and score assigned annual appraisals"),
    ("hr_eis.appraisal.finalize", "Finalize and close annual appraisals"),
    ("hr_eis.ltc.apply", "Submit LTC advance or reimbursement requests"),
    ("hr_eis.ltc.view_self", "View own LTC requests"),
    ("hr_eis.ltc.verify", "Verify LTC claim eligibility and documents"),
    ("hr_eis.ltc.approve", "Approve, reject, or forward LTC requests"),
    ("hr_eis.ltc.settle", "Record financial settlement for approved LTC claims"),
    ("hr_eis.cpda.apply", "Submit CPDA advance or reimbursement requests"),
    ("hr_eis.cpda.view_self", "View own CPDA requests"),
    ("hr_eis.cpda.verify", "Verify CPDA claim eligibility and documents"),
    ("hr_eis.cpda.approve", "Approve, reject, or forward CPDA requests"),
    ("hr_eis.cpda.settle", "Record financial disbursement for approved CPDA claims"),
    ("hr_eis.workflow.configure", "Configure HR-EIS workflow policies and submission windows"),
    ("hr_eis.audit.view", "View immutable audit logs and compliance records"),
    ("hr_eis.notification.view_self", "Receive and view HR-EIS notifications"),
]

_EMPLOYEE = [
    "hr_eis.service_record.view_self",
    "hr_eis.leave.apply",
    "hr_eis.leave.view_self",
    "hr_eis.appraisal.submit",
    "hr_eis.appraisal.view_self",
    "hr_eis.ltc.apply",
    "hr_eis.ltc.view_self",
    "hr_eis.cpda.apply",
    "hr_eis.cpda.view_self",
    "hr_eis.notification.view_self",
]

_HOD = list(_EMPLOYEE) + [
    "hr_eis.leave.review",
    "hr_eis.appraisal.review",
    "hr_eis.ltc.approve",
    "hr_eis.cpda.approve",
]

_REGISTRAR = list(_EMPLOYEE) + [
    "hr_eis.leave.review",
    "hr_eis.appraisal.review",
    "hr_eis.appraisal.finalize",
    "hr_eis.ltc.approve",
    "hr_eis.cpda.approve",
]

_DIRECTOR = list(_EMPLOYEE) + [
    "hr_eis.leave.review",
    "hr_eis.appraisal.review",
    "hr_eis.appraisal.finalize",
    "hr_eis.ltc.approve",
    "hr_eis.cpda.approve",
]

_HR_ADMIN = [
    "hr_eis.service_record.view_self",
    "hr_eis.service_record.manage",
    "hr_eis.service_record.view_all",
    "hr_eis.appraisal.assign_reviewer",
    "hr_eis.ltc.verify",
    "hr_eis.cpda.verify",
    "hr_eis.workflow.configure",
    "hr_eis.audit.view",
    "hr_eis.notification.view_self",
]

_ACCOUNTANT = [
    "hr_eis.service_record.view_self",
    "hr_eis.ltc.settle",
    "hr_eis.cpda.settle",
    "hr_eis.notification.view_self",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "hod": _HOD,
    "registrar": _REGISTRAR,
    "director": _DIRECTOR,
    "hr_admin": _HR_ADMIN,
    "accountant": _ACCOUNTANT,
}
