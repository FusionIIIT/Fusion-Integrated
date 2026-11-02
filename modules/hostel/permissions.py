"""Hostel Management permissions and role definitions."""

MODULE_CODE = "hostel"

PERMISSIONS = [
    # 3.0 Hostel Master and Role Assignment Administration (HM-UC-001..004)
    ("hostel.master.manage", "Create, activate, and deactivate hostel records"),
    ("hostel.role_binding.manage", "Assign, reassign, activate, and deactivate hostel role bindings"),

    # 3.1 & 3.2 Accommodation & Room Allotment (HM-UC-005..011)
    ("hostel.accommodation.apply", "Submit hostel accommodation requests"),
    ("hostel.accommodation.view", "View accommodation requests and status"),
    ("hostel.allotment.manage", "Record batch allotments, re-allotments, and room vacations"),
    ("hostel.room.manage", "Maintain room availability, occupancy, and individual exchanges"),
    ("hostel.room.view", "View room allocation and occupancy details"),

    # 3.3 Attendance Management (HM-UC-012, HM-UC-013, HM-UC-036)
    ("hostel.attendance.record", "Record and monitor student attendance"),
    ("hostel.attendance.view", "View student attendance status and summaries"),

    # 3.4 Leave Management (HM-UC-014..016, HM-UC-037)
    ("hostel.leave.apply", "Submit leave requests with supporting details"),
    ("hostel.leave.review", "Review and record approval or rejection on leave requests"),
    ("hostel.leave.view", "View leave requests, status, and history"),

    # 3.5 Complaint Management (HM-UC-017..019)
    ("hostel.complaint.submit", "Submit hostel-related complaints"),
    ("hostel.complaint.resolve", "Review, update, resolve, and escalate hostel complaints"),
    ("hostel.complaint.view", "View hostel complaints and resolution history"),

    # 3.6 Guest Room Booking (HM-UC-020..022)
    ("hostel.guest_room.request", "Submit guest room booking requests"),
    ("hostel.guest_room.review", "Review and record decisions on guest room bookings"),
    ("hostel.guest_room.view", "View guest room booking status and history"),

    # 3.7 Extended Stay Management (HM-UC-023..025)
    ("hostel.extended_stay.apply", "Submit extended-stay requests for vacations or breaks"),
    ("hostel.extended_stay.review", "Review and record decisions on extended-stay requests"),
    ("hostel.extended_stay.view", "View extended-stay requests and compliance status"),

    # 3.8 Fine Management (HM-UC-026, HM-UC-027, HM-UC-038)
    ("hostel.fine.record", "Record fines imposed for damages or rule violations"),
    ("hostel.fine.view", "View fine records, history, and disciplinary summaries"),

    # 3.9 Inventory & Staff Coordination (HM-UC-028, HM-UC-029, HM-UC-039)
    ("hostel.inventory.manage", "Maintain hostel operational inventory and audit logs"),
    ("hostel.inventory.view", "View hostel inventory and change logs"),
    ("hostel.staff.manage", "Maintain hostel staff assignments and duty shifts"),
    ("hostel.staff.view", "View hostel staff assignments and shift info"),

    # 3.10 Security Guard Shifts (HM-UC-030)
    ("hostel.security.manage", "Maintain security guard shift schedules and posts"),
    ("hostel.security.view", "View security guard shift schedules"),

    # 3.11 Notices & Announcements (HM-UC-031, HM-UC-032)
    ("hostel.notice.publish", "Publish hostel notices and announcements"),
    ("hostel.notice.view", "View hostel notice board and announcements"),

    # 3.12 Reports & Operational Summaries (HM-UC-033)
    ("hostel.report.view", "Generate and view hostel operational reports and summaries"),
]

SYSTEM_PERMISSIONS = [
    # System automated background notifications or sync
]
