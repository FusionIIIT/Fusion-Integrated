"""What the server tells the shell about the PHC module (ADR-0010).

Nav items carry `required_permission`; the server filters before sending, so a
link a role cannot use never reaches the browser. Permissions are granted per
designation name as it exists in globals_designation.
"""
MODULE = {
    "code": "phc", "label": "PHC", "icon": "Stethoscope",
    "base_path": "/phc", "nav_section": "PHC", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # ---- Patient ---------------------------------------------------------
    {"code": "phc.schedule", "label": "Doctor Schedule",
     "icon": "Calendar", "to": "/phc/schedule",
     "required_permission": "phc.schedule.view", "sort_order": 5},
    {"code": "phc.records", "label": "My Medical Records",
     "icon": "FileText", "to": "/phc/records",
     "required_permission": "phc.records.view_self", "sort_order": 10},
    {"code": "phc.claims", "label": "My Reimbursement Claims",
     "icon": "FileDollarSign", "to": "/phc/claims",
     "required_permission": "phc.reimbursement.view_self", "sort_order": 15},
    {"code": "phc.advisories", "label": "Health Advisories",
     "icon": "Megaphone", "to": "/phc/advisories",
     "required_permission": "phc.advisory.view", "sort_order": 20},

    # ---- PHC Staff -------------------------------------------------------
    {"code": "phc.schedule-manage", "label": "Manage Doctor Schedule",
     "icon": "Settings", "to": "/phc/staff/schedule",
     "required_permission": "phc.schedule.manage", "sort_order": 55},
    {"code": "phc.attendance", "label": "Doctor Attendance",
     "icon": "UserCheck", "to": "/phc/staff/attendance",
     "required_permission": "phc.schedule.manage", "sort_order": 60},
    {"code": "phc.patient-records", "label": "Patient Records",
     "icon": "Users", "to": "/phc/staff/patients",
     "required_permission": "phc.records.manage", "sort_order": 65},
    {"code": "phc.inventory", "label": "Inventory Stock",
     "icon": "Package", "to": "/phc/staff/inventory",
     "required_permission": "phc.inventory.adjust", "sort_order": 70},
    {"code": "phc.requisitions", "label": "Procurement Requisitions",
     "icon": "ShoppingCart", "to": "/phc/staff/requisitions",
     "required_permission": "phc.inventory.requisition.submit", "sort_order": 75},
    {"code": "phc.ambulance", "label": "Ambulance Logs",
     "icon": "Ambulance", "to": "/phc/staff/ambulance",
     "required_permission": "phc.ambulance.log", "sort_order": 80},
    {"code": "phc.advisories-manage", "label": "Publish Health Advisory",
     "icon": "Broadcast", "to": "/phc/staff/advisories",
     "required_permission": "phc.advisory.publish", "sort_order": 85},
    {"code": "phc.reports", "label": "Administrative Reports",
     "icon": "ChartBar", "to": "/phc/staff/reports",
     "required_permission": "phc.reports.generate", "sort_order": 90},

    # ---- Accounts & Audit ------------------------------------------------
    {"code": "phc.audit-verify", "label": "Verify Claims",
     "icon": "CheckCircle", "to": "/phc/audit/claims",
     "required_permission": "phc.reimbursement.verify", "sort_order": 100},
    {"code": "phc.audit-pay", "label": "Process Payments",
     "icon": "CreditCard", "to": "/phc/audit/payments",
     "required_permission": "phc.reimbursement.payment", "sort_order": 105},

    # ---- Approving Authority --------------------------------------------
    {"code": "phc.approve-requisition", "label": "Decide Requisitions",
     "icon": "Gavel", "to": "/phc/approver/requisitions",
     "required_permission": "phc.inventory.requisition.decide", "sort_order": 110},
    {"code": "phc.approve-sanction", "label": "Decide Sanctions",
     "icon": "Gavel", "to": "/phc/approver/sanctions",
     "required_permission": "phc.reimbursement.sanction", "sort_order": 115},
]

#: Every permission this module recognises.
PERMISSIONS = [
    ("phc.schedule.view", "View the published doctor schedule and attendance"),
    ("phc.schedule.manage", "Create, maintain and publish doctor schedules"),
    ("phc.records.view_self", "View one's own medical history and prescriptions"),
    ("phc.records.manage", "Create patient visit and prescription records"),
    ("phc.reimbursement.submit", "Submit a medical bill reimbursement claim"),
    ("phc.reimbursement.view_self", "Track one's own reimbursement claims"),
    ("phc.reimbursement.review", "PHC-stage review of submitted claims"),
    ("phc.reimbursement.verify", "Accounts & Audit financial verification"),
    ("phc.reimbursement.sanction", "Approve or reject a reimbursement sanction"),
    ("phc.reimbursement.payment", "Process final reimbursement payment"),
    ("phc.inventory.adjust", "Add to or deduct from inventory stock"),
    ("phc.inventory.requisition.submit", "Create and submit procurement requisitions"),
    ("phc.inventory.requisition.decide", "Approve or reject a pending requisition"),
    ("phc.inventory.requisition.fulfill", "Mark an approved requisition fulfilled"),
    ("phc.ambulance.log", "Record ambulance usage"),
    ("phc.advisory.view", "View published health advisories"),
    ("phc.advisory.publish", "Publish health advisories to patient dashboards"),
    ("phc.reports.generate", "Generate anonymized administrative reports"),
    ("phc.audit.view", "View the immutable audit trail"),
]

#: Performed by a service or scheduled task; no designation holds them.
SYSTEM_PERMISSIONS = []

_STAFF = [
    "phc.schedule.manage", "phc.records.manage", "phc.inventory.adjust",
    "phc.inventory.requisition.submit", "phc.inventory.requisition.fulfill",
    "phc.ambulance.log", "phc.advisory.publish", "phc.reports.generate",
    "phc.reimbursement.review",
]

_AUDIT = [
    "phc.reimbursement.verify", "phc.reimbursement.payment", "phc.audit.view",
]

_APPROVER = [
    "phc.reimbursement.sanction", "phc.inventory.requisition.decide",
]

_PATIENT = [
    "phc.schedule.view", "phc.records.view_self", "phc.advisory.view",
]

_EMPLOYEE = [*_PATIENT, "phc.reimbursement.submit", "phc.reimbursement.view_self"]

_STUDENT = [*_PATIENT]  # students are explicitly excluded from reimbursement

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "phc_staff": _STAFF,
    "PHC Staff": _STAFF,
    "accounts_audit": _AUDIT,
    "Accounts & Audit": _AUDIT,
    "approving_authority": _APPROVER,
    "Approving Authority": _APPROVER,
    "employee": _EMPLOYEE,
    "student": _STUDENT,
}
