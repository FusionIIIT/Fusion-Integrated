"""Hostel Management API URL routing."""

from django.urls import path
from modules.hostel.api import views as v

urlpatterns = [
    # Hostels & Role Bindings
    path("hostels", v.HostelListCreateView.as_view(), name="hostel-list"),
    path("hostels/<int:pk>", v.HostelDetailView.as_view(), name="hostel-detail"),
    path("role-bindings", v.RoleBindingListCreateView.as_view(), name="hostel-role-bindings"),

    # Rooms
    path("rooms", v.RoomListCreateView.as_view(), name="hostel-rooms"),
    path("rooms/<int:pk>", v.RoomDetailView.as_view(), name="hostel-room-detail"),

    # Accommodation Requests & Allotments
    path("requests", v.AccommodationRequestListCreateView.as_view(), name="hostel-accommodation-requests"),
    path("allotments", v.AllotmentListView.as_view(), name="hostel-allotments"),
    path("allotments/batch", v.BatchAllotmentDecisionView.as_view(), name="hostel-batch-allotment"),
    path("allotments/<int:pk>/vacate", v.RoomVacationView.as_view(), name="hostel-room-vacate"),
    path("allotments/exchange", v.RoomExchangeView.as_view(), name="hostel-room-exchange"),

    # Attendance
    path("attendance", v.AttendanceListView.as_view(), name="hostel-attendance"),

    # Leaves
    path("leaves", v.LeaveRequestListCreateView.as_view(), name="hostel-leaves"),
    path("leaves/<int:pk>/decide", v.LeaveDecideView.as_view(), name="hostel-leave-decide"),

    # Complaints
    path("complaints", v.ComplaintListCreateView.as_view(), name="hostel-complaints"),
    path("complaints/<int:pk>", v.ComplaintUpdateView.as_view(), name="hostel-complaint-update"),

    # Guest Room Bookings
    path("guest-rooms", v.GuestRoomBookingListCreateView.as_view(), name="hostel-guest-rooms"),
    path("guest-rooms/<int:pk>/decide", v.GuestRoomDecideView.as_view(), name="hostel-guest-room-decide"),

    # Extended Stay
    path("extended-stays", v.ExtendedStayListCreateView.as_view(), name="hostel-extended-stays"),
    path("extended-stays/<int:pk>/decide", v.ExtendedStayDecideView.as_view(), name="hostel-extended-stay-decide"),

    # Fines
    path("fines", v.FineListCreateView.as_view(), name="hostel-fines"),

    # Operations
    path("inventory", v.InventoryListCreateView.as_view(), name="hostel-inventory"),
    path("staff-logs", v.StaffDutyLogListCreateView.as_view(), name="hostel-staff-logs"),
    path("security-shifts", v.SecurityGuardShiftListCreateView.as_view(), name="hostel-security-shifts"),

    # Notices & Notifications
    path("notices", v.NoticeListCreateView.as_view(), name="hostel-notices"),
    path("notifications", v.NotificationListView.as_view(), name="hostel-notifications"),
    path("notifications/<int:pk>/read", v.NotificationMarkReadView.as_view(), name="hostel-notification-read"),

    # Reports
    path("reports/<int:hostel_id>", v.OperationalReportView.as_view(), name="hostel-operational-report"),
]
