"""HR-EIS API URLs."""
from django.urls import path

from modules.hreis.api import views

app_name = "hreis"

urlpatterns = [
    # Dashboard & Personal Service Record
    path("stats/", views.DashboardStatsView.as_view(), name="stats"),
    path("service-records/me/", views.MyServiceRecordView.as_view(), name="my-service-record"),
    path("service-records/", views.ServiceRecordListView.as_view(), name="service-records-list"),
    path("service-records/<int:pk>/", views.ServiceRecordDetailView.as_view(), name="service-record-detail"),

    # Leaves
    path("leaves/", views.LeaveListCreateView.as_view(), name="leaves-list-create"),
    path("leaves/<int:pk>/", views.LeaveDetailView.as_view(), name="leave-detail"),
    path("leaves/<int:pk>/decide/", views.LeaveDecideView.as_view(), name="leave-decide"),

    # Appraisals
    path("appraisals/", views.AppraisalListCreateView.as_view(), name="appraisals-list-create"),
    path("appraisals/<int:pk>/", views.AppraisalDetailView.as_view(), name="appraisal-detail"),
    path("appraisals/<int:pk>/assign-reviewers/", views.AppraisalAssignReviewersView.as_view(), name="appraisal-assign-reviewers"),
    path("appraisals/<int:pk>/review/", views.AppraisalReviewView.as_view(), name="appraisal-review"),
    path("appraisals/<int:pk>/finalize/", views.AppraisalFinalizeView.as_view(), name="appraisal-finalize"),

    # LTC
    path("ltc/", views.LtcListCreateView.as_view(), name="ltc-list-create"),
    path("ltc/<int:pk>/", views.LtcDetailView.as_view(), name="ltc-detail"),
    path("ltc/<int:pk>/verify/", views.LtcVerifyView.as_view(), name="ltc-verify"),
    path("ltc/<int:pk>/decide/", views.LtcDecideView.as_view(), name="ltc-decide"),
    path("ltc/<int:pk>/settle/", views.LtcSettleView.as_view(), name="ltc-settle"),

    # CPDA
    path("cpda/", views.CpdaListCreateView.as_view(), name="cpda-list-create"),
    path("cpda/<int:pk>/", views.CpdaDetailView.as_view(), name="cpda-detail"),
    path("cpda/<int:pk>/verify/", views.CpdaVerifyView.as_view(), name="cpda-verify"),
    path("cpda/<int:pk>/decide/", views.CpdaDecideView.as_view(), name="cpda-decide"),
    path("cpda/<int:pk>/settle/", views.CpdaSettleView.as_view(), name="cpda-settle"),

    # Admin & Workflow Configuration
    path("workflows/settings/", views.WorkflowConfigView.as_view(), name="workflow-settings"),
    path("audit-logs/", views.AuditLogListView.as_view(), name="audit-logs"),

    # Notifications
    path("notifications/", views.NotificationListView.as_view(), name="notifications-list"),
    path("notifications/<int:pk>/read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read"),
]
