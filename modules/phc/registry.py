"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "phc",
    "label": "Primary Health Centre",
    "icon": "Heartbeat",
    "base_path": "/phc",
    "nav_section": "Campus",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    # -- General / Patients / Everyone
    {
        "code": "phc.doctor_schedule",
        "label": "Doctor Schedule",
        "icon": "CalendarBlank",
        "to": "/phc/doctor-schedule",
        "required_permission": "phc.doctor_schedule.view",
        "sort_order": 10,
    },
    {
        "code": "phc.my_medical_history",
        "label": "My Health Records",
        "icon": "FileText",
        "to": "/phc/my-medical-history",
        "required_permission": "phc.patient_record.view_self",
        "sort_order": 20,
    },
    {
        "code": "phc.announcements",
        "label": "Health Advisories",
        "icon": "Megaphone",
        "to": "/phc/announcements",
        "required_permission": "phc.announcement.view",
        "sort_order": 25,
    },
    # -- Employees only (Reimbursement submission & tracking)
    {
        "code": "phc.reimbursement.apply",
        "label": "Apply Reimbursement",
        "icon": "Receipt",
        "to": "/phc/reimbursement/apply",
        "required_permission": "phc.reimbursement.create",
        "sort_order": 30,
    },
    {
        "code": "phc.reimbursement.tracking",
        "label": "My Claims",
        "icon": "ClockCounterClockwise",
        "to": "/phc/reimbursement/tracking",
        "required_permission": "phc.reimbursement.view_self",
        "sort_order": 35,
    },
    # -- Clinical & Operational Staff (PHC Staff)
    {
        "code": "phc.patient_records",
        "label": "Patient Consultations",
        "icon": "Users",
        "to": "/phc/patient-records",
        "required_permission": "phc.patient_record.manage",
        "sort_order": 40,
    },
    {
        "code": "phc.inventory",
        "label": "Pharmacy & Inventory",
        "icon": "Package",
        "to": "/phc/inventory",
        "required_permission": "phc.inventory.view",
        "sort_order": 50,
    },
    {
        "code": "phc.requisitions",
        "label": "Procurement Requisitions",
        "icon": "ClipboardText",
        "to": "/phc/requisitions",
        "required_permission": "phc.requisition.create",
        "sort_order": 55,
    },
    {
        "code": "phc.ambulance",
        "label": "Ambulance Logs",
        "icon": "Truck",
        "to": "/phc/ambulance",
        "required_permission": "phc.ambulance.manage",
        "sort_order": 60,
    },
    # -- Review / Approvals (Staff, Accounts & Audit, Approving Authority)
    {
        "code": "phc.reimbursement.queue",
        "label": "Claim Processing Queue",
        "icon": "CheckSquare",
        "to": "/phc/reimbursement/queue",
        "required_permission": "phc.reimbursement.review",
        "sort_order": 70,
    },
    # -- Administration & Governance
    {
        "code": "phc.reports",
        "label": "PHC Reports",
        "icon": "ChartBar",
        "to": "/phc/reports",
        "required_permission": "phc.report.view",
        "sort_order": 80,
    },
    {
        "code": "phc.audit",
        "label": "Audit Trail",
        "icon": "ShieldCheck",
        "to": "/phc/audit",
        "required_permission": "phc.audit.view",
        "sort_order": 90,
    },
]

PERMISSIONS = [
    ("phc.doctor_schedule.view", "View doctor schedule and live availability"),
    ("phc.doctor_schedule.manage", "Create, maintain, publish schedule and mark attendance"),
    ("phc.patient_record.view_self", "View own medical history and prescriptions"),
    ("phc.patient_record.download_self", "Download own medical records PDF"),
    ("phc.patient_record.manage", "Search patient profiles, record visits, digitize prescriptions"),
    ("phc.reimbursement.create", "Submit reimbursement claims (Employees only)"),
    ("phc.reimbursement.view_self", "View status and history of own claims"),
    ("phc.reimbursement.review", "Review reimbursement claims at PHC stage"),
    ("phc.reimbursement.verify", "Verify reimbursement claim financial details"),
    ("phc.reimbursement.sanction", "Approve or reject reimbursement sanction"),
    ("phc.reimbursement.pay", "Process payment for approved reimbursement claims"),
    ("phc.inventory.view", "View inventory stock levels and warnings"),
    ("phc.inventory.adjust", "Add or deduct inventory stock levels"),
    ("phc.requisition.create", "Submit inventory procurement requisitions"),
    ("phc.requisition.fulfill", "Mark delivered approved requisition as fulfilled"),
    ("phc.requisition.decide", "Approve or reject inventory requisitions"),
    ("phc.ambulance.manage", "Record and view ambulance usage logs"),
    ("phc.announcement.view", "View health advisories and announcements"),
    ("phc.announcement.manage", "Publish and manage health advisories"),
    ("phc.report.view", "Generate and view anonymized administrative reports"),
    ("phc.audit.view", "View immutable audit trail of sensitive-data actions"),
]

SYSTEM_PERMISSIONS = []

_PATIENT_STUDENT = [
    "phc.doctor_schedule.view",
    "phc.patient_record.view_self",
    "phc.patient_record.download_self",
    "phc.announcement.view",
]

_PATIENT_EMPLOYEE = [
    *_PATIENT_STUDENT,
    "phc.reimbursement.create",
    "phc.reimbursement.view_self",
]

_PHC_STAFF = [
    "phc.doctor_schedule.view",
    "phc.doctor_schedule.manage",
    "phc.patient_record.manage",
    "phc.inventory.view",
    "phc.inventory.adjust",
    "phc.requisition.create",
    "phc.requisition.fulfill",
    "phc.ambulance.manage",
    "phc.announcement.view",
    "phc.announcement.manage",
    "phc.reimbursement.review",
    "phc.report.view",
    "phc.audit.view",
]

_ACCOUNTS_AUDIT = [
    "phc.reimbursement.review",   # Allowed to access the processing queue page
    "phc.reimbursement.verify",
    "phc.reimbursement.pay",
    "phc.report.view",
]

_APPROVING_AUTHORITY = [
    "phc.reimbursement.review",   # Allowed to access the processing queue page
    "phc.reimbursement.sanction",
    "phc.requisition.create",     # Allowed to access requisitions page
    "phc.requisition.decide",
    "phc.report.view",
    "phc.audit.view",
]

_PHC_ADMIN = [
    *_PHC_STAFF,
    *_APPROVING_AUTHORITY,
]

ROLE_GRANTS = {
    "student": _PATIENT_STUDENT,
    "faculty": _PATIENT_EMPLOYEE,
    "staff": _PATIENT_EMPLOYEE,
    "phc_staff": _PHC_STAFF,
    "compounder": _PHC_STAFF,
    "medical_officer": _PHC_STAFF,
    "accounts_audit": _ACCOUNTS_AUDIT,
    "accountant": _ACCOUNTS_AUDIT,
    "audit_staff": _ACCOUNTS_AUDIT,
    "approving_authority": _APPROVING_AUTHORITY,
    "director": _APPROVING_AUTHORITY,
    "dean_admin": _APPROVING_AUTHORITY,
    "phc_admin": _PHC_ADMIN,
    "admin": _PHC_ADMIN,
}
