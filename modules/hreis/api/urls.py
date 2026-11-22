"""Native HR-EIS API mount, not a legacy Fusion route."""

from django.urls import path

from modules.hreis.api import views as v

urlpatterns = [
    path("service-records/me/", v.MyRecordView.as_view(), name="hreis-my-record"),
    path("service-records/", v.RecordListCreateView.as_view(), name="hreis-service-records"),
    path("service-records/<int:pk>/", v.RecordDetailView.as_view(), name="hreis-service-record"),
    path("requests/", v.RequestListView.as_view(), name="hreis-requests"),
    path(
        "requests/approvals/",
        v.ApprovalQueueView.as_view(),
        name="hreis-approval-queue",
    ),
    path("requests/<int:pk>/", v.RequestDetailView.as_view(), name="hreis-request-detail"),
    path("leave/balances/", v.MyLeaveBalancesView.as_view(), name="hreis-my-leave-balances"),
    path("requests/leave/", v.LeaveSubmitView.as_view(), name="hreis-leave-submit"),
    path(
        "leave-balances/credits/",
        v.VerifiedLeaveCreditView.as_view(),
        name="hreis-verified-leave-credit",
    ),
    path("requests/claims/", v.ClaimSubmitView.as_view(), name="hreis-claim-submit"),
    path("requests/appraisals/", v.AppraisalSubmitView.as_view(), name="hreis-appraisal-submit"),
    path(
        "requests/<int:pk>/assign-reviewers/",
        v.ReviewerAssignmentView.as_view(),
        name="hreis-assign-reviewers",
    ),
    path(
        "requests/<int:pk>/appraisal-decision/",
        v.AppraisalDecisionView.as_view(),
        name="hreis-appraisal-decision",
    ),
    path("requests/<int:pk>/verify-claim/", v.ClaimReviewView.as_view(), name="hreis-claim-review"),
    path(
        "requests/<int:pk>/financial-review/",
        v.FinancialReviewView.as_view(),
        name="hreis-financial-review",
    ),
    path(
        "requests/<int:pk>/financial-processing/",
        v.FinancialProcessingView.as_view(),
        name="hreis-financial-processing",
    ),
    path(
        "requests/<int:pk>/decision/",
        v.RequestDecisionView.as_view(),
        name="hreis-request-decision",
    ),
    path("policies/", v.PolicyListCreateView.as_view(), name="hreis-policies"),
    path("notifications/", v.NotificationListView.as_view(), name="hreis-notifications"),
    path(
        "notifications/<int:pk>/read/",
        v.NotificationMarkReadView.as_view(),
        name="hreis-mark-notification-read",
    ),
    path("audit/", v.AuditListView.as_view(), name="hreis-audit"),
    path(
        "compliance/requests/",
        v.ComplianceRequestListView.as_view(),
        name="hreis-compliance-requests",
    ),
    path(
        "compliance/requests/<int:pk>/",
        v.ComplianceRequestDetailView.as_view(),
        name="hreis-compliance-request-detail",
    ),
]
