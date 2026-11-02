from django.urls import path
try:
    from . import views
except ImportError:
    import views

urlpatterns = [
    path("hostels/", views.HostelListCreateView.as_view(), name="hostel-list-create"),
    path("accommodation/request/", views.AccommodationRequestView.as_view(), name="accommodation-request"),
    path("accommodation/allot/", views.AllotRoomView.as_view(), name="accommodation-allot"),
    path("rooms/exchange/", views.RoomExchangeView.as_view(), name="room-exchange"),
    path("attendance/", views.AttendanceView.as_view(), name="attendance"),
    path("leave/", views.LeaveRequestView.as_view(), name="leave-request"),
    path("leave/review/", views.LeaveReviewView.as_view(), name="leave-review"),
    path("complaints/", views.ComplaintView.as_view(), name="complaints"),
    path("complaints/update/", views.ComplaintUpdateView.as_view(), name="complaint-update"),
    path("guest-room/book/", views.GuestRoomBookingView.as_view(), name="guest-room-book"),
    path("extended-stay/", views.ExtendedStayView.as_view(), name="extended-stay"),
    path("fines/", views.FineView.as_view(), name="fines"),
    path("notices/", views.NoticeView.as_view(), name="notices"),
    path("reports/summary/", views.OperationalReportView.as_view(), name="operational-report"),
]
