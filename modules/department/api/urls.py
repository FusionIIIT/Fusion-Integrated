"""URL routing for Department module API."""
from django.urls import path
from modules.department.api import views

app_name = "department"

urlpatterns = [
    # Graduate Seminar Scheduling (BW-OAP-09)
    path("requests/", views.SeminarRequestListCreateView.as_view(), name="request-list-create"),
    path("requests/<int:pk>/", views.SeminarRequestDetailView.as_view(), name="request-detail"),
    path("pending/", views.PendingSeminarsListView.as_view(), name="pending-list"),
    path("requests/<int:pk>/schedule/", views.ScheduleSeminarView.as_view(), name="schedule-seminar"),
    path("requests/<int:pk>/reject/", views.RejectSeminarView.as_view(), name="reject-seminar"),
    path("seminars/", views.ScheduledSeminarListView.as_view(), name="scheduled-list"),
    path("seminars/<int:pk>/", views.ScheduledSeminarDetailView.as_view(), name="scheduled-detail"),

    # Allocations (AFR-OAP-043, AFR-OAP-044)
    path("allocations/ta/", views.TAAllocationListCreateView.as_view(), name="ta-allocation-list-create"),
    path("allocations/supervisors/", views.SupervisorAllocationListCreateView.as_view(), name="supervisor-allocation-list-create"),

    # Announcements
    path("announcements/", views.AnnouncementListCreateView.as_view(), name="announcement-list-create"),
]
