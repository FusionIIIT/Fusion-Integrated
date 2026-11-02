"""REST API URL routes for Hostel Management."""

from django.urls import path

from . import views

app_name = "hostel"

urlpatterns = [
    # Hostels & Role Bindings
    path("hostels/", views.HostelListCreateView.as_view(), name="hostel-list"),
    path("hostels/<int:pk>/", views.HostelDetailView.as_view(), name="hostel-detail"),
    path(
        "hostels/<int:pk>/toggle-active/",
        views.HostelToggleActiveView.as_view(),
        name="hostel-toggle-active",
    ),
    path(
        "role-bindings/", views.HostelRoleBindingListCreateView.as_view(), name="role-binding-list"
    ),
    path(
        "role-bindings/<int:pk>/deactivate/",
        views.HostelRoleBindingDeactivateView.as_view(),
        name="role-binding-deactivate",
    ),
    # Rooms & Occupancy
    path("rooms/", views.RoomListCreateView.as_view(), name="room-list"),
    path("rooms/<int:pk>/status/", views.RoomStatusUpdateView.as_view(), name="room-status-update"),
    path("rooms/exchange/", views.RoomExchangeView.as_view(), name="room-exchange"),
    # Accommodation & Allotment
    path(
        "accommodation-requests/",
        views.AccommodationRequestListCreateView.as_view(),
        name="accommodation-request-list",
    ),
    path("allotments/", views.RoomAllotmentListCreateView.as_view(), name="allotment-list"),
    path(
        "allotments/<int:pk>/vacate/",
        views.RoomAllotmentVacateView.as_view(),
        name="allotment-vacate",
    ),
    # Attendance
    path("attendance/", views.AttendanceRecordListCreateView.as_view(), name="attendance-list"),
    # Leaves
    path("leaves/", views.HostelLeaveListCreateView.as_view(), name="leave-list"),
    path("leaves/<int:pk>/decide/", views.HostelLeaveDecideView.as_view(), name="leave-decide"),
    # Complaints
    path("complaints/", views.HostelComplaintListCreateView.as_view(), name="complaint-list"),
    path(
        "complaints/<int:pk>/update-status/",
        views.HostelComplaintUpdateView.as_view(),
        name="complaint-update-status",
    ),
    # Guest Rooms
    path("guest-rooms/", views.GuestRoomBookingListCreateView.as_view(), name="guest-room-list"),
    path(
        "guest-rooms/<int:pk>/decide/",
        views.GuestRoomBookingDecideView.as_view(),
        name="guest-room-decide",
    ),
    # Extended Stays
    path(
        "extended-stays/",
        views.ExtendedStayRequestListCreateView.as_view(),
        name="extended-stay-list",
    ),
    path(
        "extended-stays/<int:pk>/decide/",
        views.ExtendedStayRequestDecideView.as_view(),
        name="extended-stay-decide",
    ),
    path(
        "extended-stays/<int:pk>/compliance/",
        views.ExtendedStayComplianceView.as_view(),
        name="extended-stay-compliance",
    ),
    # Fines & Discipline
    path("fines/", views.HostelFineListCreateView.as_view(), name="fine-list"),
    path(
        "fines/<int:pk>/update-status/",
        views.HostelFineStatusUpdateView.as_view(),
        name="fine-update-status",
    ),
    # Operations: Inventory & Staff
    path("inventory/", views.HostelInventoryListCreateView.as_view(), name="inventory-list"),
    path("staff/", views.HostelStaffListCreateView.as_view(), name="staff-list"),
    # Security Shifts
    path(
        "security-shifts/", views.SecurityShiftListCreateView.as_view(), name="security-shift-list"
    ),
    # Notices & Bulletin
    path("notices/", views.HostelNoticeListCreateView.as_view(), name="notice-list"),
    # In-app Notifications
    path("notifications/", views.HostelNotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<int:pk>/read/",
        views.HostelNotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    # Reports & Dashboards
    path("reports/", views.HostelReportsView.as_view(), name="hostel-reports"),
    path(
        "reports/summary/",
        views.HostelExecutiveSummaryView.as_view(),
        name="hostel-executive-summary",
    ),
    path(
        "dashboard/stats/", views.HostelDashboardStatsView.as_view(), name="hostel-dashboard-stats"
    ),
]
