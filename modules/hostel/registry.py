"""What the server tells the shell about Hostel Management (HM)."""

from .permissions import PERMISSIONS as _PERMS_TYPED

MODULE = {
    "code": "hostel",
    "label": "Hostel Management",
    "icon": "Buildings",
    "base_path": "/hostel",
    "nav_section": "Campus",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- General / Dashboard --------------------------------------------------
    {
        "code": "hostel.dashboard",
        "label": "Hostel Overview",
        "icon": "Buildings",
        "to": "/hostel/dashboard",
        "required_permission": "hostel.notice.view",
        "sort_order": 10,
    },
    # -- Super Admin: Master & Role Bindings ----------------------------------
    {
        "code": "hostel.master",
        "label": "Hostels & Administration",
        "icon": "GearSix",
        "to": "/hostel/master",
        "required_permission": "hostel.hostel.manage",
        "sort_order": 20,
    },
    # -- Staff: Allotment rounds & Room inventory -----------------------------
    {
        "code": "hostel.allotments",
        "label": "Allotments & Requests",
        "icon": "UsersThree",
        "to": "/hostel/allotments",
        "required_permission": "hostel.accommodation.allot",
        "sort_order": 30,
    },
    {
        "code": "hostel.occupancy",
        "label": "Rooms & Occupancy",
        "icon": "Door",
        "to": "/hostel/occupancy",
        "required_permission": "hostel.room.view",
        "sort_order": 40,
    },
    # -- Attendance ----------------------------------------------------------
    {
        "code": "hostel.attendance",
        "label": "Student Attendance",
        "icon": "CheckSquare",
        "to": "/hostel/attendance",
        "required_permission": "hostel.attendance.record",
        "sort_order": 50,
    },
    # -- Leaves --------------------------------------------------------------
    {
        "code": "hostel.leaves",
        "label": "Leave Requests",
        "icon": "CalendarDots",
        "to": "/hostel/leaves",
        "required_permission": "hostel.leave.review",
        "sort_order": 60,
    },
    # -- Complaints ----------------------------------------------------------
    {
        "code": "hostel.complaints",
        "label": "Hostel Complaints",
        "icon": "Wrench",
        "to": "/hostel/complaints",
        "required_permission": "hostel.complaint.manage",
        "sort_order": 70,
    },
    # -- Guest Rooms ---------------------------------------------------------
    {
        "code": "hostel.guest_rooms",
        "label": "Guest Rooms",
        "icon": "Bed",
        "to": "/hostel/guest-rooms",
        "required_permission": "hostel.guest_room.manage",
        "sort_order": 80,
    },
    # -- Extended Stays ------------------------------------------------------
    {
        "code": "hostel.extended_stays",
        "label": "Extended Stays",
        "icon": "ClockAfternoon",
        "to": "/hostel/extended-stays",
        "required_permission": "hostel.extended_stay.review",
        "sort_order": 90,
    },
    # -- Fines & Discipline --------------------------------------------------
    {
        "code": "hostel.fines",
        "label": "Fines & Disciplinary",
        "icon": "Receipt",
        "to": "/hostel/fines",
        "required_permission": "hostel.fine.record",
        "sort_order": 100,
    },
    # -- Operations: Inventory & Staff ---------------------------------------
    {
        "code": "hostel.inventory",
        "label": "Inventory & Staff",
        "icon": "Package",
        "to": "/hostel/inventory",
        "required_permission": "hostel.inventory.manage",
        "sort_order": 110,
    },
    # -- Security Shift Schedule ---------------------------------------------
    {
        "code": "hostel.security",
        "label": "Security Roster",
        "icon": "ShieldCheck",
        "to": "/hostel/security",
        "required_permission": "hostel.security.schedule",
        "sort_order": 120,
    },
    # -- Notice Board --------------------------------------------------------
    {
        "code": "hostel.notices",
        "label": "Notice Board",
        "icon": "Megaphone",
        "to": "/hostel/notices",
        "required_permission": "hostel.notice.view",
        "sort_order": 130,
    },
    # -- Operational Reports -------------------------------------------------
    {
        "code": "hostel.reports",
        "label": "Operational Reports",
        "icon": "ChartBar",
        "to": "/hostel/reports",
        "required_permission": "hostel.report.view",
        "sort_order": 140,
    },
]

#: Plain tuples (code, label) for permission_manifest collector
PERMISSIONS = [(p.code, p.label) for p in _PERMS_TYPED]

SYSTEM_PERMISSIONS = [
    "hostel.notification.auto_emit",
]

_STUDENT = [
    "hostel.accommodation.request",
    "hostel.accommodation.view_self",
    "hostel.attendance.view_self",
    "hostel.leave.request",
    "hostel.leave.view_self",
    "hostel.complaint.submit",
    "hostel.complaint.view_self",
    "hostel.guest_room.request",
    "hostel.guest_room.view_self",
    "hostel.extended_stay.request",
    "hostel.extended_stay.view_self",
    "hostel.fine.view_self",
    "hostel.notice.view",
    "hostel.room.view",
]

_CARETAKER = [
    "hostel.hostel.view",
    "hostel.role_binding.view",
    "hostel.room.view",
    "hostel.room.manage",
    "hostel.accommodation.allot",
    "hostel.accommodation.request",
    "hostel.attendance.record",
    "hostel.attendance.view",
    "hostel.leave.review",
    "hostel.complaint.manage",
    "hostel.complaint.escalate",
    "hostel.guest_room.manage",
    "hostel.fine.record",
    "hostel.fine.manage",
    "hostel.inventory.manage",
    "hostel.staff.manage",
    "hostel.notice.publish",
    "hostel.notice.view",
    "hostel.report.view",
]

_WARDEN = [
    "hostel.hostel.view",
    "hostel.role_binding.view",
    "hostel.room.view",
    "hostel.attendance.view",
    "hostel.leave.review",
    "hostel.complaint.escalate",
    "hostel.extended_stay.review",
    "hostel.fine.manage",
    "hostel.staff.manage",
    "hostel.security.schedule",
    "hostel.notice.publish",
    "hostel.notice.view",
    "hostel.report.view",
]

_SUPER_ADMIN = [
    "hostel.hostel.view",
    "hostel.hostel.manage",
    "hostel.role_binding.view",
    "hostel.role_binding.manage",
    "hostel.room.view",
    "hostel.room.manage",
    "hostel.accommodation.allot",
    "hostel.accommodation.request",
    "hostel.accommodation.view_self",
    "hostel.attendance.record",
    "hostel.attendance.view",
    "hostel.attendance.view_self",
    "hostel.leave.request",
    "hostel.leave.review",
    "hostel.leave.view_self",
    "hostel.complaint.submit",
    "hostel.complaint.manage",
    "hostel.complaint.escalate",
    "hostel.complaint.view_self",
    "hostel.guest_room.request",
    "hostel.guest_room.manage",
    "hostel.guest_room.view_self",
    "hostel.extended_stay.request",
    "hostel.extended_stay.review",
    "hostel.extended_stay.view_self",
    "hostel.fine.record",
    "hostel.fine.manage",
    "hostel.fine.view_self",
    "hostel.inventory.manage",
    "hostel.staff.manage",
    "hostel.security.schedule",
    "hostel.notice.publish",
    "hostel.notice.view",
    "hostel.report.view",
    "hostel.report.view_institution",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "hostel_caretaker": _CARETAKER,
    "hostel_warden": _WARDEN,
    "super_admin": _SUPER_ADMIN,
    "admin": _SUPER_ADMIN,
}
