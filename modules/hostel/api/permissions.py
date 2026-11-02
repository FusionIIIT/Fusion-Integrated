"""DRF Permission helpers for Hostel Management."""

from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE = HasModuleGrant("hostel")

# Convenient shortcuts
P_HOSTEL_VIEW = HasPermission("hostel.hostel.view")
P_HOSTEL_MANAGE = HasPermission("hostel.hostel.manage")
P_ROLE_MANAGE = HasPermission("hostel.role_binding.manage")
P_ROOM_VIEW = HasPermission("hostel.room.view")
P_ROOM_MANAGE = HasPermission("hostel.room.manage")
P_ACCOM_REQUEST = HasPermission("hostel.accommodation.request")
P_ACCOM_ALLOT = HasPermission("hostel.accommodation.allot")
P_ACCOM_VIEW_SELF = HasPermission("hostel.accommodation.view_self")
P_ATTENDANCE_RECORD = HasPermission("hostel.attendance.record")
P_ATTENDANCE_VIEW = HasPermission("hostel.attendance.view", "hostel.attendance.view_self")
P_LEAVE_REQUEST = HasPermission("hostel.leave.request")
P_LEAVE_REVIEW = HasPermission("hostel.leave.review")
P_LEAVE_VIEW = HasPermission(
    "hostel.leave.review", "hostel.leave.view_self", "hostel.leave.request"
)
P_COMPLAINT_SUBMIT = HasPermission("hostel.complaint.submit")
P_COMPLAINT_MANAGE = HasPermission("hostel.complaint.manage", "hostel.complaint.escalate")
P_COMPLAINT_VIEW = HasPermission(
    "hostel.complaint.manage", "hostel.complaint.view_self", "hostel.complaint.submit"
)
P_GUEST_REQUEST = HasPermission("hostel.guest_room.request")
P_GUEST_MANAGE = HasPermission("hostel.guest_room.manage")
P_GUEST_VIEW = HasPermission(
    "hostel.guest_room.manage", "hostel.guest_room.view_self", "hostel.guest_room.request"
)
P_EXTENDED_REQUEST = HasPermission("hostel.extended_stay.request")
P_EXTENDED_REVIEW = HasPermission("hostel.extended_stay.review")
P_EXTENDED_VIEW = HasPermission(
    "hostel.extended_stay.review", "hostel.extended_stay.view_self", "hostel.extended_stay.request"
)
P_FINE_RECORD = HasPermission("hostel.fine.record")
P_FINE_MANAGE = HasPermission("hostel.fine.manage")
P_FINE_VIEW = HasPermission("hostel.fine.record", "hostel.fine.manage", "hostel.fine.view_self")
P_INVENTORY_MANAGE = HasPermission("hostel.inventory.manage")
P_STAFF_MANAGE = HasPermission("hostel.staff.manage")
P_SECURITY_SCHEDULE = HasPermission("hostel.security.schedule")
P_NOTICE_PUBLISH = HasPermission("hostel.notice.publish")
P_NOTICE_VIEW = HasPermission("hostel.notice.view")
P_REPORT_VIEW = HasPermission("hostel.report.view", "hostel.report.view_institution")
