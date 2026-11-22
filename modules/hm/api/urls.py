from django.urls import path
from modules.hm.api import views

app_name = "hm"

urlpatterns = [
    # Hostels
    path("hostels", views.HostelListCreateView.as_view(), name="hostel-list-create"),
    path("hostels/<int:id>", views.HostelDetailUpdateView.as_view(), name="hostel-detail-update"),
    path("hostels/<int:id>/role-bindings", views.HostelRoleBindingListCreateView.as_view(), name="hostel-role-binding-list-create"),
    path("role-bindings/<int:id>", views.HostelRoleBindingRevokeView.as_view(), name="hostel-role-binding-revoke"),

    # Accommodation
    path("accommodation-requests", views.AccommodationRequestListCreateView.as_view(), name="accommodation-request-list-create"),
    path("accommodation-requests/<int:id>/allot", views.AccommodationRequestAllotView.as_view(), name="accommodation-request-allot"),

    # Rooms
    path("rooms", views.RoomListView.as_view(), name="room-list"),
    path("rooms/<int:id>", views.RoomDetailUpdateView.as_view(), name="room-detail-update"),
    path("room-assignments", views.RoomAssignmentListView.as_view(), name="room-assignment-list"),
    path("room-assignments/<int:id>/vacate", views.RoomAssignmentVacateView.as_view(), name="room-assignment-vacate"),
    path("room-assignments/<int:id>/exchange", views.RoomAssignmentExchangeView.as_view(), name="room-assignment-exchange"),

    # Attendance
    path("attendance", views.AttendanceListCreateView.as_view(), name="attendance-list-create"),
    path("attendance/summary", views.AttendanceSummaryView.as_view(), name="attendance-summary"),

    # Leave
    path("leave-requests", views.LeaveRequestListCreateView.as_view(), name="leave-request-list-create"),
    path("leave-requests/<int:id>/decision", views.LeaveRequestDecisionView.as_view(), name="leave-request-decision"),
    path("leave-requests/summary", views.LeaveRequestSummaryView.as_view(), name="leave-request-summary"),

    # Complaints
    path("complaints", views.ComplaintListCreateView.as_view(), name="complaint-list-create"),
    path("complaints/<int:id>/events", views.ComplaintEventCreateView.as_view(), name="complaint-event-create"),
    path("complaints/summary", views.ComplaintSummaryView.as_view(), name="complaint-summary"),

    # Guest Bookings
    path("guest-bookings", views.GuestBookingListCreateView.as_view(), name="guest-booking-list-create"),
    path("guest-bookings/<int:id>/decision", views.GuestBookingDecisionView.as_view(), name="guest-booking-decision"),

    # Extended Stays
    path("extended-stays", views.ExtendedStayListCreateView.as_view(), name="extended-stay-list-create"),
    path("extended-stays/<int:id>/decision", views.ExtendedStayDecisionView.as_view(), name="extended-stay-decision"),

    # Fines
    path("fines", views.FineListCreateView.as_view(), name="fine-list-create"),
    path("fines/summary", views.FineSummaryView.as_view(), name="fine-summary"),

    # Inventory
    path("inventory", views.InventoryListCreateView.as_view(), name="inventory-list-create"),
    path("inventory/<int:id>", views.InventoryUpdateView.as_view(), name="inventory-update"),

    # Guard Shifts
    path("guard-shifts", views.GuardShiftListCreateView.as_view(), name="guard-shift-list-create"),

    # Notices
    path("notices", views.NoticeListCreateView.as_view(), name="notice-list-create"),
    path("notices/<int:id>/publish", views.NoticePublishView.as_view(), name="notice-publish"),
    path("notices/<int:id>/withdraw", views.NoticeWithdrawView.as_view(), name="notice-withdraw"),

    # Reports
    path("reports/<str:report_code>", views.ReportView.as_view(), name="report-view"),
]
