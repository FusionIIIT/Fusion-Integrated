"""Permission definitions for Hostel Management."""

from typing import NamedTuple


class P(NamedTuple):
    code: str
    label: str
    dangerous: bool = False


MODULE_CODE = "hostel"

PERMISSIONS = [
    # Hostel Master & Roles (CFR-HM-001, 002)
    P("hostel.hostel.view", "View hostel master records"),
    P("hostel.hostel.manage", "Create, activate, or deactivate hostels", dangerous=True),
    P("hostel.role_binding.view", "View hostel role assignments"),
    P(
        "hostel.role_binding.manage",
        "Assign, reassign, or revoke hostel warden/caretaker bindings",
        dangerous=True,
    ),
    # Accommodation & Rooms (CFR-HM-003..008)
    P("hostel.accommodation.request", "Submit hostel accommodation request"),
    P("hostel.accommodation.allot", "Record hostel and room allotment decisions"),
    P("hostel.accommodation.view_self", "View own room allotment and occupancy details"),
    P("hostel.room.view", "View room availability and occupancy"),
    P("hostel.room.manage", "Maintain rooms, record exchanges and formal vacations"),
    # Attendance (CFR-HM-009..011)
    P("hostel.attendance.record", "Record student daily attendance"),
    P("hostel.attendance.view", "Review attendance summaries, trends, and exceptions"),
    P("hostel.attendance.view_self", "View own attendance records and percentages"),
    # Leaves (CFR-HM-012..014)
    P("hostel.leave.request", "Submit hostel leave request"),
    P("hostel.leave.review", "Review and record leave decisions"),
    P("hostel.leave.view_self", "View own leave status and history"),
    # Complaints (CFR-HM-015..018)
    P("hostel.complaint.submit", "Submit hostel complaint"),
    P("hostel.complaint.manage", "Review, assign, and resolve complaints"),
    P("hostel.complaint.escalate", "Escalate complaints to Warden or review escalated complaints"),
    P("hostel.complaint.view_self", "View own submitted complaints and resolution updates"),
    # Guest Rooms (CFR-HM-019..021)
    P("hostel.guest_room.request", "Submit guest room booking request"),
    P("hostel.guest_room.manage", "Review guest room booking and assign room"),
    P("hostel.guest_room.view_self", "View own guest room booking status"),
    # Extended Stays (CFR-HM-022..024)
    P("hostel.extended_stay.request", "Submit vacation / break extended stay request"),
    P("hostel.extended_stay.review", "Review extended stay requests, set charges and compliance"),
    P("hostel.extended_stay.view_self", "View own extended stay status and compliance deadlines"),
    # Fines & Discipline (CFR-HM-025..027)
    P("hostel.fine.record", "Record and impose hostel disciplinary fines"),
    P("hostel.fine.manage", "Review and resolve or waive disciplinary fines"),
    P("hostel.fine.view_self", "View own fine records and payment details"),
    # Inventory & Staff (CFR-HM-028)
    P("hostel.inventory.manage", "Maintain hostel inventory records"),
    P("hostel.staff.manage", "Maintain hostel operational staff coordination and shifts"),
    # Security Shifts (CFR-HM-029)
    P("hostel.security.schedule", "Maintain security guard shift schedules"),
    # Notices (CFR-HM-030)
    P("hostel.notice.publish", "Publish hostel notices and announcements"),
    P("hostel.notice.view", "View active hostel notice board"),
    # Reports (CFR-HM-031, 032)
    P("hostel.report.view", "Generate hostel reports and operational summaries"),
    P("hostel.report.view_institution", "View institution-level cross-hostel summaries"),
    # System Tasks / Automated (CFR-HM-033)
    P("hostel.notification.auto_emit", "System automated event notifications"),
]
