"""IAM permission and navigation contract for the PHC module."""

MODULE = {
    "code": "phc",
    "label": "Primary Health Centre",
    "icon": "FirstAid",
    "base_path": "/phc",
    "nav_section": "Health",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "phc.schedule",
        "label": "Doctor Schedule",
        "icon": "CalendarCheck",
        "to": "/phc/schedule",
        "required_permission": "phc.schedule.view",
        "sort_order": 10,
    },
    {
        "code": "phc.my_records",
        "label": "My Medical Records",
        "icon": "FileMedical",
        "to": "/phc/my/visits",
        "required_permission": "phc.record.view_self",
        "sort_order": 20,
    },
    {
        "code": "phc.claims",
        "label": "My Reimbursement Claims",
        "icon": "Receipt",
        "to": "/phc/claims/my",
        "required_permission": "phc.claim.view_self",
        "sort_order": 30,
    },
    {
        "code": "phc.announcements",
        "label": "Health Advisories",
        "icon": "Megaphone",
        "to": "/phc/announcements",
        "required_permission": "phc.schedule.view",
        "sort_order": 40,
    },
    {
        "code": "phc.inventory",
        "label": "Inventory",
        "icon": "Package",
        "to": "/phc/inventory",
        "required_permission": "phc.inventory.manage",
        "sort_order": 50,
    },
    {
        "code": "phc.requisitions",
        "label": "Procurement Requisitions",
        "icon": "ClipboardList",
        "to": "/phc/requisitions",
        "required_permission": "phc.requisition.submit",
        "sort_order": 60,
    },
    {
        "code": "phc.ambulance",
        "label": "Ambulance Log",
        "icon": "Ambulance",
        "to": "/phc/ambulance",
        "required_permission": "phc.ambulance.log",
        "sort_order": 70,
    },
    {
        "code": "phc.reports",
        "label": "Reports",
        "icon": "ChartBar",
        "to": "/phc/reports",
        "required_permission": "phc.report.view",
        "sort_order": 80,
    },
]

_PHC_STAFF = [
    "phc.schedule.manage",
    "phc.attendance.mark",
    "phc.record.manage",
    "phc.inventory.manage",
    "phc.requisition.submit",
    "phc.requisition.fulfill",
    "phc.ambulance.log",
    "phc.announcement.publish",
    "phc.report.view",
    "phc.claim.review_phc",
    "phc.claim.configure",
]

ROLE_GRANTS = {
    "phc_staff": _PHC_STAFF,
    "patient": ["phc.schedule.view", "phc.record.view_self"],
    "employee": [
        "phc.schedule.view",
        "phc.record.view_self",
        "phc.claim.submit",
        "phc.claim.view_self",
    ],
    "accounts_audit": ["phc.claim.verify", "phc.claim.payment"],
    "approving_authority": [
        "phc.claim.decide",
        "phc.requisition.decide",
    ],
}

PERMISSIONS = [
    ("phc.schedule.view", "View doctor schedule"),
    ("phc.schedule.manage", "Create and publish doctor schedules"),
    ("phc.attendance.mark", "Mark doctor real-time attendance"),
    ("phc.record.view_self", "View own medical records"),
    ("phc.record.manage", "Create and manage patient records"),
    ("phc.claim.submit", "Submit a reimbursement claim"),
    ("phc.claim.view_self", "View own reimbursement claims"),
    ("phc.claim.review_phc", "PHC Staff review of reimbursement claims"),
    ("phc.claim.verify", "Accounts & Audit: verify reimbursement"),
    ("phc.claim.decide", "Approving Authority: decide reimbursement sanction"),
    ("phc.claim.payment", "Accounts & Audit: process reimbursement payment"),
    ("phc.claim.configure", "Configure the reimbursement submission window"),
    ("phc.inventory.manage", "Manage PHC inventory stock"),
    ("phc.requisition.submit", "Submit procurement requisitions"),
    ("phc.requisition.decide", "Approve or reject procurement requisitions"),
    ("phc.requisition.fulfill", "Mark requisition as fulfilled"),
    ("phc.ambulance.log", "Record ambulance usage"),
    ("phc.announcement.publish", "Publish health advisories"),
    ("phc.report.view", "Generate PHC administrative reports"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []
