"""URL routing for Hostel Management module."""

from django.urls import path

from modules.hostel.api.views import (
    AccommodationListCreateView,
    AttendanceCreateView,
    ComplaintActionView,
    ComplaintListCreateView,
    FineListCreateView,
    HostelListView,
    LeaveActionView,
    LeaveListCreateView,
    NoticeListCreateView,
)

urlpatterns = [
    path("hostels/", HostelListView.as_view(), name="hostels-list"),
    path(
        "accommodations/",
        AccommodationListCreateView.as_view(),
        name="accommodations-list-create",
    ),
    path("leaves/", LeaveListCreateView.as_view(), name="leaves-list-create"),
    path("leaves/<int:pk>/action/", LeaveActionView.as_view(), name="leaves-action"),
    path(
        "complaints/",
        ComplaintListCreateView.as_view(),
        name="complaints-list-create",
    ),
    path(
        "complaints/<int:pk>/action/",
        ComplaintActionView.as_view(),
        name="complaints-action",
    ),
    path("attendances/", AttendanceCreateView.as_view(), name="attendances-create"),
    path("fines/", FineListCreateView.as_view(), name="fines-list-create"),
    path("notices/", NoticeListCreateView.as_view(), name="notices-list-create"),
]
