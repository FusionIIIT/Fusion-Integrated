"""Hostel Management API URL patterns."""

from django.urls import path
from .views import (
    AccommodationRequestListCreateView,
    AllotmentDecisionView,
    AllotmentListView,
    AllotmentReallotView,
    AllotmentVacateView,
    AttendanceListCreateView,
    ComplaintListCreateView,
    ComplaintStatusView,
    ExtendedStayComplianceView,
    ExtendedStayDecisionView,
    ExtendedStayListCreateView,
    FineListCreateView,
    GuestBookingDecisionView,
    GuestBookingListCreateView,
    HostelDetailView,
    HostelListCreateView,
    HostelToggleActiveView,
    InventoryAuditListView,
    InventoryListCreateView,
    LeaveDecisionView,
    LeaveRequestListCreateView,
    NoticeListCreateView,
    NotificationListView,
    NotificationMarkReadView,
    ReportsView,
    RoleBindingListCreateView,
    RoomExchangeView,
    RoomHistoryListView,
    RoomListCreateView,
    SecurityShiftListCreateView,
    StaffAssignmentListCreateView,
)

urlpatterns = [
    # Hostel Master & Role Bindings
    path("hostels/", HostelListCreateView.as_view(), name="hostel-list-create"),
    path("hostels/<int:pk>/", HostelDetailView.as_view(), name="hostel-detail"),
    path("hostels/<int:pk>/toggle-active/", HostelToggleActiveView.as_view(), name="hostel-toggle-active"),
    path("role-bindings/", RoleBindingListCreateView.as_view(), name="role-binding-list-create"),

    # Rooms & Caretaker Room Exchange
    path("rooms/", RoomListCreateView.as_view(), name="room-list-create"),
    path("rooms/exchange/", RoomExchangeView.as_view(), name="room-exchange"),

    # Accommodation & Allotment Lifecycle
    path("accommodation-requests/", AccommodationRequestListCreateView.as_view(), name="accommodation-request-list-create"),
    path("accommodation-requests/<int:pk>/allot/", AllotmentDecisionView.as_view(), name="allotment-decision"),
    path("allotments/", AllotmentListView.as_view(), name="allotment-list"),
    path("allotments/<int:pk>/reallot/", AllotmentReallotView.as_view(), name="allotment-reallot"),
    path("allotments/<int:pk>/vacate/", AllotmentVacateView.as_view(), name="allotment-vacate"),
    path("allotments/history/", RoomHistoryListView.as_view(), name="room-history-list"),

    # Attendance
    path("attendance/", AttendanceListCreateView.as_view(), name="attendance-list-create"),

    # Leave Management
    path("leaves/", LeaveRequestListCreateView.as_view(), name="leave-list-create"),
    path("leaves/<int:pk>/decision/", LeaveDecisionView.as_view(), name="leave-decision"),

    # Complaints
    path("complaints/", ComplaintListCreateView.as_view(), name="complaint-list-create"),
    path("complaints/<int:pk>/status/", ComplaintStatusView.as_view(), name="complaint-status"),

    # Guest Rooms
    path("guest-rooms/", GuestBookingListCreateView.as_view(), name="guest-booking-list-create"),
    path("guest-rooms/<int:pk>/decision/", GuestBookingDecisionView.as_view(), name="guest-booking-decision"),

    # Vacation Extended Stay
    path("extended-stay/", ExtendedStayListCreateView.as_view(), name="extended-stay-list-create"),
    path("extended-stay/<int:pk>/decision/", ExtendedStayDecisionView.as_view(), name="extended-stay-decision"),
    path("extended-stay/<int:pk>/compliance/", ExtendedStayComplianceView.as_view(), name="extended-stay-compliance"),

    # Fines
    path("fines/", FineListCreateView.as_view(), name="fine-list-create"),

    # Inventory & Staff Coordination
    path("inventory/", InventoryListCreateView.as_view(), name="inventory-list-create"),
    path("inventory/audits/", InventoryAuditListView.as_view(), name="inventory-audit-list"),
    path("staff/", StaffAssignmentListCreateView.as_view(), name="staff-list-create"),

    # Security Guard Shifts
    path("security-shifts/", SecurityShiftListCreateView.as_view(), name="security-shift-list-create"),

    # Notices
    path("notices/", NoticeListCreateView.as_view(), name="notice-list-create"),

    # Operational Reports
    path("reports/", ReportsView.as_view(), name="reports-view"),

    # In-App Notifications
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-read"),
]
