MODULE = {
    "code": "hostel_management",
    "label": "Hostel Management",
    "icon": "Bed",
    "base_path": "/hostel",
    "nav_section": "Hostel",
    "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "hostel.dashboard", "label": "Dashboard", "icon": "Home", "to": "/hostel", "required_permission": "hostel.view", "sort_order": 10},
    {"code": "hostel.warden_bindings", "label": "Warden Role Bindings", "icon": "UserCheck", "to": "/hostel/warden-bindings", "required_permission": "hostel.manage_warden_bindings", "sort_order": 20},
    {"code": "hostel.caretaker_bindings", "label": "Caretaker Role Bindings", "icon": "CalendarBlank", "to": "/hostel/caretaker-bindings", "required_permission": "hostel.manage_caretaker_bindings", "sort_order": 30},
]

PERMISSIONS = [
    ("hostel.view", "View hostel data and dashboard"),
    ("hostel.manage_warden_bindings", "Manage Warden role bindings"),
    ("hostel.manage_caretaker_bindings", "Manage Caretaker role bindings"),
]

ROLE_GRANTS = {
    "student": ["hostel.view"],
    "warden": ["hostel.view", "hostel.manage_warden_bindings"],
    "caretaker": ["hostel.view", "hostel.manage_caretaker_bindings"],
    "super_admin": ["hostel.view", "hostel.manage_warden_bindings", "hostel.manage_caretaker_bindings"],
}
