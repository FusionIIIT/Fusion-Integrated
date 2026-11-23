"""What the server tells the shell about the PHC module (ADR-0010)."""
MODULE = {
    "code": "phc", "label": "Primary Health Centre", "icon": "FirstAidKit",
    "base_path": "/phc", "nav_section": "Health Services", "sort_order": 50,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "phc.schedule", "label": "Doctor Schedule", "icon": "Stethoscope",
     "to": "/phc/schedule", "required_permission": "phc.schedule.view", "sort_order": 10},
    {"code": "phc.advisories", "label": "Health Advisories", "icon": "Megaphone",
     "to": "/phc/advisories", "required_permission": "phc.advisory.view", "sort_order": 15},
    {"code": "phc.records", "label": "Medical Records", "icon": "FileText",
     "to": "/phc/records", "required_permission": "phc.record.view", "sort_order": 20},
    {"code": "phc.claims", "label": "Reimbursements", "icon": "Receipt",
     "to": "/phc/claims", "required_permission": "phc.claim.view", "sort_order": 30},
    {"code": "phc.inventory", "label": "Inventory", "icon": "Package",
     "to": "/phc/inventory", "required_permission": "phc.inventory.view", "sort_order": 40},
    {"code": "phc.requisitions", "label": "Requisitions", "icon": "ListChecks",
     "to": "/phc/requisitions", "required_permission": "phc.requisition.view",
     "sort_order": 50},
    {"code": "phc.ambulance", "label": "Ambulance Log", "icon": "Ambulance",
     "to": "/phc/ambulance", "required_permission": "phc.ambulance.view", "sort_order": 60},
    {"code": "phc.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/phc/reports", "required_permission": "phc.report.view", "sort_order": 70},
    {"code": "phc.notifications", "label": "Notifications", "icon": "Bell",
     "to": "/phc/notifications", "required_permission": "phc.notification.view",
     "sort_order": 80},
]

PERMISSIONS = [
    ("phc.schedule.view", "See the published doctor schedule and today's attendance"),
    ("phc.schedule.create", "Create doctor schedules"),
    ("phc.schedule.update", "Maintain doctor schedules"),
    ("phc.schedule.publish", "Publish doctor schedules to patients"),
    ("phc.attendance.update", "Mark visiting doctors Available or Departed"),
    ("phc.patient.view", "Search patient profiles"),
    ("phc.record.view", "See medical records within one's scope"),
    ("phc.record.create", "Record patient visits and prescriptions"),
    ("phc.claim.view", "See reimbursement claims within one's scope"),
    ("phc.claim.create", "Submit a medical bill reimbursement claim"),
    ("phc.claim.review", "Review claims at the PHC stage and forward them"),
    ("phc.claim.update", "Verify claims and record reimbursement payments"),
    ("phc.claim.approve", "Approve or reject reimbursement sanctions"),
    ("phc.inventory.view", "See inventory and low-stock alerts"),
    ("phc.inventory.create", "Add inventory items"),
    ("phc.inventory.update", "Add to or deduct from stock"),
    ("phc.requisition.view", "See procurement requisitions within one's scope"),
    ("phc.requisition.create", "Raise procurement requisitions"),
    ("phc.requisition.approve", "Approve or reject procurement requisitions"),
    ("phc.requisition.update", "Mark approved requisitions fulfilled"),
    ("phc.ambulance.view", "See the ambulance log"),
    ("phc.ambulance.create", "Log ambulance use"),
    ("phc.advisory.view", "See health advisories"),
    ("phc.advisory.publish", "Publish health advisories"),
    ("phc.report.view", "Generate anonymised PHC reports"),
    ("phc.notification.view", "See one's own PHC notifications"),
]

SYSTEM_PERMISSIONS: list[str] = []
SCOPE_PERMISSIONS: list[str] = []

_PATIENT = [
    "phc.schedule.view",
    "phc.advisory.view",
    "phc.record.view",
    "phc.notification.view",
]

# PHC-BR-04: reimbursement belongs to employees only.
_EMPLOYEE = [*_PATIENT, "phc.claim.view", "phc.claim.create"]

_PHC_STAFF = [
    "phc.schedule.view",
    "phc.schedule.create",
    "phc.schedule.update",
    "phc.schedule.publish",
    "phc.attendance.update",
    "phc.patient.view",
    "phc.record.view",
    "phc.record.create",
    "phc.claim.view",
    "phc.claim.review",
    "phc.inventory.view",
    "phc.inventory.create",
    "phc.inventory.update",
    "phc.requisition.view",
    "phc.requisition.create",
    "phc.requisition.update",
    "phc.ambulance.view",
    "phc.ambulance.create",
    "phc.advisory.view",
    "phc.advisory.publish",
    "phc.report.view",
    "phc.notification.view",
]

_ACCOUNTS = ["phc.claim.view", "phc.claim.update"]

_AUTHORITY = [
    "phc.claim.view",
    "phc.claim.approve",
    "phc.requisition.view",
    "phc.requisition.approve",
]

# Office designations use the spec's actor names; see blueprint open question 2.
ROLE_GRANTS = {
    "student": _PATIENT,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "PHC Staff": _PHC_STAFF,
    "Accounts & Audit": _ACCOUNTS,
    "Approving Authority": _AUTHORITY,
}


def readiness() -> list[str]:
    from django.utils import timezone

    from modules.phc.selectors.policy import active_policy

    if active_policy(timezone.localdate()) is None:
        return [("No reimbursement submission window is in effect (PHC-BR-06). Run "
                 "`manage.py phc_configure_window --days <n> --includes-last-day yes|no`.")]
    return []
