"""Permission classes for Hostel Management endpoints."""

from rest_framework.permissions import BasePermission
from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal

# Module gate
RequireHostelModule = HasModuleGrant("hostel")

# Action-level gates
CanManageHostelMaster = HasPermission("hostel.master.manage")
CanManageRoleBindings = HasPermission("hostel.role_binding.manage")
CanApplyAccommodation = HasPermission("hostel.accommodation.apply")
CanViewAccommodation = HasPermission("hostel.accommodation.view")
CanManageAllotments = HasPermission("hostel.allotment.manage")
CanManageRooms = HasPermission("hostel.room.manage")
CanViewRooms = HasPermission("hostel.room.view")
CanRecordAttendance = HasPermission("hostel.attendance.record")
CanViewAttendance = HasPermission("hostel.attendance.view")
CanApplyLeave = HasPermission("hostel.leave.apply")
CanReviewLeave = HasPermission("hostel.leave.review")
CanViewLeave = HasPermission("hostel.leave.view")
CanSubmitComplaint = HasPermission("hostel.complaint.submit")
CanResolveComplaint = HasPermission("hostel.complaint.resolve")
CanViewComplaint = HasPermission("hostel.complaint.view")
CanRequestGuestRoom = HasPermission("hostel.guest_room.request")
CanReviewGuestRoom = HasPermission("hostel.guest_room.review")
CanViewGuestRoom = HasPermission("hostel.guest_room.view")
CanApplyExtendedStay = HasPermission("hostel.extended_stay.apply")
CanReviewExtendedStay = HasPermission("hostel.extended_stay.review")
CanViewExtendedStay = HasPermission("hostel.extended_stay.view")
CanRecordFine = HasPermission("hostel.fine.record")
CanViewFine = HasPermission("hostel.fine.view")
CanManageInventory = HasPermission("hostel.inventory.manage")
CanViewInventory = HasPermission("hostel.inventory.view")
CanManageStaff = HasPermission("hostel.staff.manage")
CanViewStaff = HasPermission("hostel.staff.view")
CanManageSecurity = HasPermission("hostel.security.manage")
CanViewSecurity = HasPermission("hostel.security.view")
CanPublishNotice = HasPermission("hostel.notice.publish")
CanViewNotice = HasPermission("hostel.notice.view")
CanViewReports = HasPermission("hostel.report.view")
