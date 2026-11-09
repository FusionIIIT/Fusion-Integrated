"""Permissions this module recognises. No nav: it has no screens of its own."""

PERMISSIONS = [
    ("phc.doctor_schedule.view", "View Doctor Schedule"),
    ("phc.doctor_schedule.create", "Create Doctor Schedule"),
    ("phc.doctor_schedule.update", "Update Doctor Schedule"),
    ("phc.doctor_schedule.publish", "Publish Doctor Schedule"),
    ("phc.doctor_attendance.update", "Update Doctor Attendance"),
    ("phc.medical_record.view", "View Medical Record"),
    ("phc.medical_record.export", "Export Medical Record"),
    ("phc.patient_record.view", "View Patient Record"),
    ("phc.patient_record.create", "Create Patient Record"),
    ("phc.reimbursement.create", "Create Reimbursement"),
    ("phc.reimbursement.view", "View Reimbursement"),
    ("phc.reimbursement.review", "Review Reimbursement"),
    ("phc.reimbursement_audit.review", "Review Reimbursement Audit"),
    ("phc.reimbursement.approve", "Approve Reimbursement"),
    ("phc.reimbursement_payment.create", "Create Reimbursement Payment"),
    ("phc.inventory.view", "View Inventory"),
    ("phc.inventory.update", "Update Inventory"),
    ("phc.requisition.create", "Create Requisition"),
    ("phc.requisition.approve", "Approve Requisition"),
    ("phc.requisition.update", "Update Requisition"),
    ("phc.ambulance_log.create", "Create Ambulance Log"),
    ("phc.announcement.view", "View Announcement"),
    ("phc.announcement.publish", "Publish Announcement"),
    ("phc.report.view", "View Report"),
]

SYSTEM_PERMISSIONS = []

_PATIENT = ["phc.doctor_schedule.view", "phc.medical_record.view", "phc.medical_record.export", "phc.announcement.view"]
_EMPLOYEE = _PATIENT + ["phc.reimbursement.create", "phc.reimbursement.view"]
_PHC_STAFF = ["phc.doctor_schedule.view", "phc.doctor_schedule.create", "phc.doctor_schedule.update", "phc.doctor_schedule.publish", "phc.doctor_attendance.update", "phc.patient_record.view", "phc.patient_record.create", "phc.reimbursement.review", "phc.inventory.view", "phc.inventory.update", "phc.requisition.create", "phc.requisition.update", "phc.ambulance_log.create", "phc.announcement.view", "phc.announcement.publish", "phc.report.view"]
_ACCOUNTS_AUDIT = ["phc.reimbursement_audit.review", "phc.reimbursement_payment.create"]
_APPROVING_AUTHORITY = ["phc.reimbursement.approve", "phc.requisition.approve"]

ROLE_GRANTS = {
    "student": _PATIENT,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "phc_staff": _PHC_STAFF,
    "phc_accounts_audit": _ACCOUNTS_AUDIT,
    "phc_approving_authority": _APPROVING_AUTHORITY
}

MODULE = {
    "code": "phc",
    "label": "Primary Health Care Centre",
    "icon": "FirstAid",
    "base_path": "/phc",
    "nav_section": "Health",
    "sort_order": 30,
    "status": "planned"
}

NAV_ITEMS = []
