"""URL configuration for Complaint Management System API."""
from django.urls import path

from modules.complaints.api import views

app_name = "complaints"

urlpatterns = [
    # Complaint listing & creation
    path("", views.ComplaintListCreateView.as_view(), name="complaint_list_create"),
    path("<int:pk>/", views.ComplaintDetailView.as_view(), name="complaint_detail"),
    path("<str:pk>/detail/", views.ComplaintDetailView.as_view(), name="complaint_detail_by_code"),
    # Operational actions
    path("<int:pk>/assign/", views.ComplaintAssignView.as_view(), name="complaint_assign"),
    path("<int:pk>/progress/", views.ComplaintProgressView.as_view(), name="complaint_progress"),
    path("<int:pk>/resolve/", views.ComplaintResolveView.as_view(), name="complaint_resolve"),
    path("<int:pk>/reject/", views.ComplaintRejectView.as_view(), name="complaint_reject"),
    path("<int:pk>/verify-close/", views.ComplaintVerifyCloseView.as_view(), name="complaint_verify_close"),
    path("<int:pk>/reopen-request/", views.ComplaintReopenRequestView.as_view(), name="complaint_reopen_request"),
    path("<int:pk>/reopen-review/", views.ComplaintReopenReviewView.as_view(), name="complaint_reopen_review"),
    path("<int:pk>/escalate/", views.ComplaintManualEscalateView.as_view(), name="complaint_manual_escalate"),
    path("<int:pk>/feedback/", views.ComplaintFeedbackView.as_view(), name="complaint_feedback"),
    # SLA autonomous trigger / check
    path("sla-check/", views.ComplaintSlaCheckView.as_view(), name="complaint_sla_check"),
    # Metadata & Management
    path("categories/", views.ComplaintCategoryListView.as_view(), name="complaint_categories"),
    path("announcements/", views.ComplaintAnnouncementListView.as_view(), name="complaint_announcements"),
    path("reports/summary/", views.ComplaintReportsSummaryView.as_view(), name="complaint_reports_summary"),
    path("roles/", views.CmsRoleAssignmentListView.as_view(), name="cms_role_assignments"),
]
