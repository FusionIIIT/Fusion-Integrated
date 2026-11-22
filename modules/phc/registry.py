from django.utils import timezone

from modules.phc.models import ReimbursementPolicy

MODULE = {
    "code": "phc",
    "label": "Primary Health Centre",
    "icon": "FirstAid",
    "base_path": "/phc",
    "nav_section": "Health",
    "sort_order": 21,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "phc.dashboard", "label": "Patient Dashboard",
     "icon": "House", "to": "/phc/patient-dashboard",
     "required_permission": "phc.patient_record.view", "sort_order": 5},
    {"code": "phc.availability", "label": "Doctor Availability",
     "icon": "CalendarDots", "to": "/phc/doctor-availability",
     "required_permission": "phc.doctor_schedule.view", "sort_order": 10},
    {"code": "phc.records", "label": "My Medical Records",
     "icon": "FirstAid", "to": "/phc/medical-records",
     "required_permission": "phc.patient_record.view", "sort_order": 20},
    {"code": "phc.claims", "label": "My Reimbursement Claims",
     "icon": "Receipt", "to": "/phc/reimbursements",
     "required_permission": "phc.reimbursement.view", "sort_order": 30},
    {"code": "phc.visits", "label": "Patient Visits",
     "icon": "ClipboardText", "to": "/phc/staff/visits",
     "required_permission": "phc.patient_record.create", "sort_order": 40},
    {"code": "phc.schedules", "label": "Doctor Schedules",
     "icon": "CalendarPlus", "to": "/phc/staff/schedules",
     "required_permission": "phc.doctor_schedule.update", "sort_order": 50},
    {"code": "phc.attendance", "label": "Doctor Attendance",
     "icon": "UserCheck", "to": "/phc/staff/attendance",
     "required_permission": "phc.doctor_attendance.update", "sort_order": 60},
    {"code": "phc.inventory", "label": "Inventory",
     "icon": "Package", "to": "/phc/staff/inventory",
     "required_permission": "phc.inventory.view", "sort_order": 70},
    {"code": "phc.requisitions", "label": "Inventory Requisitions",
     "icon": "ListChecks", "to": "/phc/staff/requisitions",
     "required_permission": "phc.requisition.view", "sort_order": 80},
    {"code": "phc.ambulance", "label": "Ambulance Log",
     "icon": "Ambulance", "to": "/phc/staff/ambulance",
     "required_permission": "phc.ambulance_usage.view", "sort_order": 90},
    {"code": "phc.advisories", "label": "Health Advisories",
     "icon": "Megaphone", "to": "/phc/advisories",
     "required_permission": "phc.advisory.view", "sort_order": 100},
    {"code": "phc.advisory_publish", "label": "Publish Health Advisories",
     "icon": "Megaphone", "to": "/phc/staff/advisories",
     "required_permission": "phc.advisory.publish", "sort_order": 105},
    {"code": "phc.reports", "label": "PHC Reports",
     "icon": "ChartBar", "to": "/phc/staff/reports",
     "required_permission": "phc.report.view", "sort_order": 110},
    {"code": "phc.notifications", "label": "PHC Notifications",
     "icon": "Bell", "to": "/phc/notifications",
     "required_permission": "phc.notification.view", "sort_order": 120},
    {"code": "phc.accounts_claims", "label": "Reimbursement Verification and Payment",
     "icon": "Receipt", "to": "/phc/accounts/claims",
     "required_permission": "phc.reimbursement.manage", "sort_order": 130},
    {"code": "phc.authority_claims", "label": "Reimbursement Sanctions",
     "icon": "Stamp", "to": "/phc/authority/claims",
     "required_permission": "phc.reimbursement.approve", "sort_order": 140},
    {"code": "phc.authority_requisitions", "label": "Requisition Decisions",
     "icon": "Stamp", "to": "/phc/authority/requisitions",
     "required_permission": "phc.requisition.approve", "sort_order": 150},
]

PERMISSIONS = [
    ("phc.doctor_schedule.view", "View published doctor schedules"),
    ("phc.doctor_schedule.create", "Create doctor schedule slots"),
    ("phc.doctor_schedule.update", "Maintain doctor schedule slots"),
    ("phc.doctor_schedule.publish", "Publish doctor schedule slots"),
    ("phc.doctor_attendance.update", "Update doctor attendance"),
    ("phc.patient_record.view", "View patient records in the caller's permitted scope"),
    ("phc.patient_record.create", "Record patient visits and prescriptions"),
    ("phc.record.export", "Download own medical records as PDF"),
    ("phc.reimbursement.view", "View claims in the caller's permitted scope"),
    ("phc.reimbursement.create", "Submit a medical reimbursement claim"),
    ("phc.reimbursement.review", "Review and forward a reimbursement claim"),
    ("phc.reimbursement.manage", "Verify and process reimbursement claims"),
    ("phc.reimbursement.approve", "Approve or reject reimbursement sanction"),
    ("phc.inventory.view", "View inventory and low-stock alerts"),
    ("phc.inventory.create", "Create inventory items"),
    ("phc.inventory.update", "Record inventory stock adjustments"),
    ("phc.requisition.view", "View requisitions in the caller's permitted scope"),
    ("phc.requisition.create", "Submit inventory requisitions"),
    ("phc.requisition.approve", "Approve or reject an inventory requisition"),
    ("phc.requisition.update", "Mark an approved requisition fulfilled"),
    ("phc.ambulance_usage.view", "View ambulance usage records"),
    ("phc.ambulance_usage.create", "Record ambulance usage"),
    ("phc.advisory.view", "View published health advisories"),
    ("phc.advisory.publish", "Publish health advisories"),
    ("phc.report.view", "Generate aggregate-only PHC reports"),
    ("phc.notification.view", "View caller-addressed PHC notifications"),
    ("phc.notification.manage", "Deliver PHC notifications as scheduled work"),
]

SYSTEM_PERMISSIONS = ["phc.notification.manage"]
SCOPE_PERMISSIONS = [
    "phc.patient_record.view",
    "phc.record.export",
    "phc.reimbursement.view",
    "phc.requisition.view",
    "phc.notification.view",
]
_PATIENT = ["phc.doctor_schedule.view", "phc.patient_record.view",
            "phc.record.export", "phc.advisory.view"]
_EMPLOYEE = [*_PATIENT, "phc.record.export", "phc.reimbursement.view",
             "phc.reimbursement.create", "phc.notification.view"]
_COMPOUNDER = [
    "phc.doctor_schedule.view", "phc.doctor_schedule.create",
    "phc.doctor_schedule.update", "phc.doctor_schedule.publish",
    "phc.doctor_attendance.update", "phc.patient_record.view",
    "phc.patient_record.create", "phc.reimbursement.view",
    "phc.reimbursement.review", "phc.inventory.view", "phc.inventory.create",
    "phc.inventory.update", "phc.requisition.view", "phc.requisition.create",
    "phc.requisition.update", "phc.ambulance_usage.view",
    "phc.ambulance_usage.create", "phc.advisory.view", "phc.advisory.publish",
    "phc.report.view", "phc.notification.view",
]

ROLE_GRANTS = {
    "student": _PATIENT,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Compounder": _COMPOUNDER,
    "Accounts Admin": ["phc.reimbursement.view", "phc.reimbursement.manage",
                        "phc.notification.view"],
    "Registrar": ["phc.reimbursement.view", "phc.reimbursement.approve",
                  "phc.requisition.view", "phc.requisition.approve",
                  "phc.notification.view"],
}


def readiness() -> list[str]:
    today = timezone.localdate()
    if not ReimbursementPolicy.objects.filter(effective_period__contains=today).exists():
        return ["Seed the effective-dated 30-day PHC reimbursement policy before enabling claims."]
    return []
