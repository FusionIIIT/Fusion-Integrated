from django.urls import path

from modules.hreis.api import views as v

urlpatterns = [
    path("records/me", v.MyRecordView.as_view(), name="hr-my-record"),
    path("records", v.RecordAdminView.as_view(), name="hr-records"),
    path("records/<int:user_id>", v.RecordAdminDetailView.as_view(), name="hr-record-update"),
    path("leave", v.LeaveListView.as_view(), name="hr-leave"),
    path("leave/<int:pk>/decision", v.LeaveDecisionView.as_view(), name="hr-leave-decision"),
    path("appraisals", v.AppraisalListView.as_view(), name="hr-appraisals"),
    path("appraisals/<int:pk>/assign", v.AppraisalAssignView.as_view(), name="hr-appraisal-assign"),
    path("appraisals/<int:pk>/review", v.AppraisalReviewView.as_view(), name="hr-appraisal-review"),
    path("claims", v.ClaimListView.as_view(), name="hr-claims"),
    path("claims/<int:pk>/verify", v.ClaimVerifyView.as_view(), name="hr-claim-verify"),
    path("claims/<int:pk>/decision", v.ClaimDecisionView.as_view(), name="hr-claim-decision"),
    path("claims/<int:pk>/process", v.ClaimProcessView.as_view(), name="hr-claim-process"),
    path("approvals", v.ApprovalQueueView.as_view(), name="hr-approvals"),
    path("routes", v.RoutesAdminView.as_view(), name="hr-routes"),
    path("windows", v.WindowsAdminView.as_view(), name="hr-windows"),
    path("audit", v.AuditView.as_view(), name="hr-audit"),
    path("notifications", v.NotificationsView.as_view(), name="hr-notifications"),
    path(
        "notifications/<int:pk>/read", v.ReadNotificationView.as_view(), name="hr-notification-read"
    ),
    path("notifications/policy", v.PolicyNotificationView.as_view(), name="hr-policy-notification"),
]
