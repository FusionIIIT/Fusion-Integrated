from django.urls import path

from modules.complaints.api import views as v

urlpatterns = [
    path("complaints", v.ComplaintListCreateView.as_view(), name="complaints-list-create"),
    path("work-queue", v.HandlerQueueView.as_view(), name="complaints-handler-queue"),
    path("assignment-queue", v.AssignmentQueueView.as_view(), name="complaints-assignment-queue"),
    path("handlers", v.HandlerOptionsView.as_view(), name="complaints-handler-options"),
    path("escalated", v.EscalatedQueueView.as_view(), name="complaints-escalated-queue"),
    path("complaints/<uuid:reference>", v.ComplaintDetailView.as_view(), name="complaints-detail"),
    path(
        "complaints/<uuid:reference>/assign",
        v.ComplaintAssignmentView.as_view(),
        name="complaints-assign",
    ),
    path(
        "complaints/<uuid:reference>/progress",
        v.ComplaintProgressView.as_view(),
        name="complaints-progress",
    ),
    path(
        "complaints/<uuid:reference>/resolve",
        v.ComplaintResolveView.as_view(),
        name="complaints-resolve",
    ),
    path(
        "complaints/<uuid:reference>/reject",
        v.ComplaintRejectView.as_view(),
        name="complaints-reject",
    ),
    path(
        "complaints/<uuid:reference>/escalate",
        v.ComplaintManualEscalationView.as_view(),
        name="complaints-escalate",
    ),
    path(
        "complaints/<uuid:reference>/history",
        v.ComplaintHistoryView.as_view(),
        name="complaints-history",
    ),
    path(
        "complaints/<uuid:reference>/attachments",
        v.ComplaintAttachmentListCreateView.as_view(),
        name="complaints-attachments",
    ),
    path(
        "attachments/<int:attachment_id>/download",
        v.ComplaintAttachmentDownloadView.as_view(),
        name="complaints-attachment-download",
    ),
    path(
        "complaints/<uuid:reference>/verify/user",
        v.UserClosureVerificationView.as_view(),
        name="complaints-verify-user",
    ),
    path(
        "complaints/<uuid:reference>/verify/supervisor",
        v.SupervisorClosureVerificationView.as_view(),
        name="complaints-verify-supervisor",
    ),
    path(
        "complaints/<uuid:reference>/feedback",
        v.FeedbackCreateView.as_view(),
        name="complaints-feedback",
    ),
    path(
        "complaints/<uuid:reference>/reopening-requests",
        v.ReopeningRequestCreateView.as_view(),
        name="complaints-reopening-request",
    ),
    path("announcements", v.AnnouncementListCreateView.as_view(), name="complaints-announcements"),
    path("reopening-requests", v.ReopeningQueueView.as_view(), name="complaints-reopening-queue"),
    path("closures/pending", v.PendingClosureView.as_view(), name="complaints-closures-pending"),
    path(
        "reopening-requests/<int:request_id>/decision",
        v.ReopeningDecisionView.as_view(),
        name="complaints-reopening-decision",
    ),
    path("feedback", v.FeedbackReviewView.as_view(), name="complaints-feedback-review"),
    path("reports", v.ComplaintReportView.as_view(), name="complaints-reports"),
    path(
        "escalations/summary",
        v.EscalationSummaryView.as_view(),
        name="complaints-escalation-summary",
    ),
]
