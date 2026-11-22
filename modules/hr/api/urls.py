from django.urls import path

from modules.hr.api import views

app_name = "hr"

urlpatterns = [
    path("employees/", views.EmployeeListView.as_view(), name="employee-list"),
    path("employees/create/", views.EmployeeCreateView.as_view(), name="employee-create"),
    path("employees/<int:user_id>/", views.EmployeeDetailView.as_view(), name="employee-detail"),
    path(
        "employees/<int:user_id>/update/",
        views.EmployeeUpdateView.as_view(),
        name="employee-update",
    ),
    path("claims/", views.ClaimListView.as_view(), name="claim-list"),
    path("claims/create/", views.ClaimCreateView.as_view(), name="claim-create"),
    path("claims/<int:pk>/", views.ClaimDetailView.as_view(), name="claim-detail"),
    path("claims/<int:pk>/verify/", views.ClaimVerificationView.as_view(), name="claim-verify"),
    path("claims/<int:pk>/decision/", views.ClaimDecisionView.as_view(), name="claim-decision"),
    path(
        "claims/<int:pk>/processing/", views.ClaimProcessingView.as_view(), name="claim-processing"
    ),
    path(
        "claims/<int:pk>/integration-status/",
        views.ClaimIntegrationStatusView.as_view(),
        name="claim-integration",
    ),
    path("claims/<int:pk>/history/", views.ClaimHistoryView.as_view(), name="claim-history"),
    path("appraisals/", views.AppraisalListView.as_view(), name="appraisal-list"),
    path("appraisals/create/", views.AppraisalCreateView.as_view(), name="appraisal-create"),
    path("appraisals/<int:pk>/", views.AppraisalDetailView.as_view(), name="appraisal-detail"),
    path(
        "appraisals/<int:pk>/reviewers/",
        views.AppraisalReviewerAssignmentView.as_view(),
        name="appraisal-reviewers",
    ),
    path(
        "appraisals/<int:pk>/review/", views.AppraisalReviewView.as_view(), name="appraisal-review"
    ),
    path("workflow-routes/", views.WorkflowRouteListView.as_view(), name="workflow-route-list"),
    path(
        "workflow-routes/save/", views.WorkflowRouteSaveView.as_view(), name="workflow-route-save"
    ),
    path(
        "appraisal-windows/", views.AppraisalWindowListView.as_view(), name="appraisal-window-list"
    ),
    path(
        "appraisal-windows/save/",
        views.AppraisalWindowSaveView.as_view(),
        name="appraisal-window-save",
    ),
    path("audit-events/", views.AuditEventListView.as_view(), name="audit-event-list"),
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notices/", views.NoticePublishView.as_view(), name="notice-publish"),
    path("leaves/", views.LeaveRequestListView.as_view(), name="leave-list"),
    path("leaves/create/", views.LeaveRequestCreateView.as_view(), name="leave-create"),
    path(
        "leaves/<int:pk>/decision/", views.LeaveRequestDecisionView.as_view(), name="leave-decision"
    ),
    path("leave-balances/", views.LeaveBalanceListView.as_view(), name="leave-balance-list"),
    path("leave-balances/save/", views.LeaveBalanceSaveView.as_view(), name="leave-balance-save"),
]
