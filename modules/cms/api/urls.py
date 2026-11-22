from django.urls import path

from modules.cms.api import views as v

urlpatterns = [
    path("config", v.CmsConfigView.as_view(), name="cms-config"),
    path("complaints", v.ComplaintListCreateView.as_view(), name="cms-complaints"),
    path("complaints/mine", v.MyComplaintsView.as_view(), name="cms-my-complaints"),
    path("complaints/<int:pk>", v.ComplaintDetailView.as_view(), name="cms-complaint"),
    path("complaints/<int:pk>/handling", v.HandlingSetupView.as_view(), name="cms-handling"),
    path("complaints/<int:pk>/progress", v.ProgressView.as_view(), name="cms-progress"),
    path("complaints/<int:pk>/outcome", v.OutcomeView.as_view(), name="cms-outcome"),
    path("complaints/<int:pk>/closure/user", v.UserClosureView.as_view(), name="cms-close-user"),
    path(
        "complaints/<int:pk>/closure/supervisor",
        v.SupervisorClosureView.as_view(),
        name="cms-close-supervisor",
    ),
    path("complaints/<int:pk>/reopening", v.ReopeningRequestView.as_view(), name="cms-reopen"),
    path("reopening-requests", v.ReopeningReviewListView.as_view(), name="cms-reopen-requests"),
    path(
        "reopening-requests/<int:pk>/decision",
        v.ReopeningDecisionView.as_view(),
        name="cms-reopen-decision",
    ),
    path("complaints/<int:pk>/escalation", v.EscalationView.as_view(), name="cms-escalate"),
    path("escalations", v.EscalatedComplaintsView.as_view(), name="cms-escalations"),
    path(
        "complaints/<int:pk>/feedback",
        v.FeedbackSubmitView.as_view(),
        name="cms-feedback-submit",
    ),
    path("feedback", v.FeedbackReviewView.as_view(), name="cms-feedback-review"),
    path("announcements", v.AnnouncementListCreateView.as_view(), name="cms-announcements"),
    path("reports", v.ReportsView.as_view(), name="cms-reports"),
    path("roles", v.RoleAssignmentView.as_view(), name="cms-roles"),
    path(
        "complaints/<int:pk>/attachments",
        v.ComplaintAttachmentView.as_view(),
        name="cms-attachments",
    ),
    path(
        "attachments/<int:pk>/download",
        v.AttachmentDownloadView.as_view(),
        name="cms-attachment-download",
    ),
]
