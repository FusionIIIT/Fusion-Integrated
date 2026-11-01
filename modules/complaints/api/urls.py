"""URL routing for Complaint Management System API."""
from django.urls import path

from modules.complaints.api import views as v

urlpatterns = [
    # Core complaints list & create
    path("", v.ComplaintListCreateView.as_view(), name="complaints-list-create"),
    path("<int:pk>/", v.ComplaintDetailView.as_view(), name="complaints-detail"),
    path("<int:pk>/setup/", v.ComplaintHandlingSetupView.as_view(), name="complaints-setup"),
    path("<int:pk>/progress/", v.ComplaintProgressUpdateView.as_view(), name="complaints-progress"),
    path("<int:pk>/resolve/", v.ComplaintResolveView.as_view(), name="complaints-resolve"),
    path("<int:pk>/reject/", v.ComplaintRejectView.as_view(), name="complaints-reject"),
    path("<int:pk>/verify/", v.ComplaintVerifyClosureView.as_view(), name="complaints-verify"),
    path("<int:pk>/reopen/", v.ComplaintReopeningRequestView.as_view(), name="complaints-reopen-request"),
    path("reopenings/<int:pk>/review/", v.ComplaintReopeningReviewView.as_view(), name="complaints-reopen-review"),
    path("<int:pk>/feedback/", v.ComplaintFeedbackView.as_view(), name="complaints-feedback"),
    path("feedback/", v.ComplaintFeedbackListView.as_view(), name="complaints-feedback-list"),
    path("<int:pk>/escalate/", v.ComplaintEscalateView.as_view(), name="complaints-escalate"),

    # Announcements, Roles, Reports
    path("announcements/", v.AnnouncementListCreateView.as_view(), name="complaints-announcements"),
    path("roles/", v.CMSRoleManagementView.as_view(), name="complaints-roles"),
    path("reports/", v.CMSOperationalReportView.as_view(), name="complaints-reports"),
]
