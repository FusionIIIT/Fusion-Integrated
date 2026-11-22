"""PHC permission catalogue and server-driven navigation."""

MODULE = {
    "code": "phc",
    "label": "Health Center",
    "icon": "FaIdCard",
    "base_path": "/phc",
    "nav_section": "Campus",
    "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS = [
    {
        "code": "phc.appointments",
        "label": "Appointments",
        "icon": "FaCalendarAlt",
        "to": "/phc/appointments",
        "required_permission": "phc.appointment.view_self",
        "sort_order": 10,
    },
    {
        "code": "phc.patients",
        "label": "Patients",
        "icon": "FaUsers",
        "to": "/phc/patients",
        "required_permission": "phc.patient.view_self",
        "sort_order": 20,
    },
    {
        "code": "phc.inventory",
        "label": "Medicine Inventory",
        "icon": "FaClipboardList",
        "to": "/phc/inventory",
        "required_permission": "phc.inventory.view",
        "sort_order": 30,
    },
    {
        "code": "phc.consultations",
        "label": "Consultations",
        "icon": "FaIdBadge",
        "to": "/phc/consultations",
        "required_permission": "phc.consultation.record",
        "sort_order": 35,
    },
    {
        "code": "phc.schedules",
        "label": "Doctor Schedules",
        "icon": "FaCalendarAlt",
        "to": "/phc/schedules",
        "required_permission": "phc.appointment.manage",
        "sort_order": 36,
    },
    {
        "code": "phc.announcements",
        "label": "Announcements",
        "icon": "FaBullhorn",
        "to": "/phc/announcements",
        "required_permission": "phc.announcement.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("phc.patient.register_self", "Register own patient record"),
    ("phc.patient.register", "Register institute patients"),
    ("phc.patient.view", "View patient records"),
    ("phc.patient.view_self", "View own patient record"),
    ("phc.appointment.view_self", "View own appointments"),
    ("phc.appointment.view", "View PHC appointments"),
    ("phc.appointment.view_all", "View all PHC appointments"),
    ("phc.appointment.book", "Book an appointment"),
    ("phc.appointment.manage", "Manage appointments and schedules"),
    ("phc.doctor.register", "Register PHC doctors"),
    ("phc.consultation.view", "View clinical records"),
    ("phc.consultation.view_all", "View all clinical records"),
    ("phc.consultation.record", "Record consultations and prescriptions"),
    ("phc.inventory.view", "View medicine inventory"),
    ("phc.inventory.manage", "Manage medicine stock"),
    ("phc.announcement.view", "View PHC announcements"),
    ("phc.announcement.publish", "Publish PHC announcements"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = ["phc.appointment.view_all", "phc.consultation.view_all"]

_PATIENT = [
    "phc.patient.register_self",
    "phc.patient.view_self",
    "phc.appointment.view_self",
    "phc.appointment.book",
    "phc.announcement.view",
]
_STAFF = [
    "phc.patient.register",
    "phc.patient.view",
    "phc.patient.view_self",
    "phc.appointment.view",
    "phc.appointment.manage",
    "phc.inventory.view",
    "phc.doctor.register",
    "phc.announcement.view",
    "phc.announcement.publish",
]
_CLINICIAN = [p for p in _STAFF if p != "phc.doctor.register"]
_CLINICIAN += ["phc.consultation.view", "phc.consultation.record"]
_ADMIN = [
    *_CLINICIAN,
    "phc.appointment.view_all",
    "phc.consultation.view_all",
    "phc.doctor.register",
    "phc.inventory.manage",
]

# Role names are designation values seeded in IAM. Deployments must assign these
# PHC designations to existing institute accounts before activating the module.
ROLE_GRANTS = {
    "student": _PATIENT,
    "faculty": _PATIENT,
    "staff": _PATIENT,
    "Doctor": _CLINICIAN,
    "Compounder": _STAFF,
    "PHC Admin": _ADMIN,
}
