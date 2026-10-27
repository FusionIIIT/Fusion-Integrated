"""URL routing for Leave Management module."""
from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("balances/", v.MyBalancesView.as_view(), name="leave-balances"),
    path("applications/", v.MyApplicationsView.as_view(), name="leave-applications"),
    path("applications/<int:pk>/", v.ApplicationDetailView.as_view(), name="leave-application-detail"),
    path("applications/<int:pk>/export/", v.ExportApplicationView.as_view(), name="leave-application-export"),
    path("applications/<int:pk>/print/", v.PrintableApplicationView.as_view(), name="leave-application-print"),
    path("applications/<int:pk>/cancel/", v.RequestCancellationView.as_view(), name="leave-cancel-request"),
    path("applications/<int:pk>/extend/", v.RequestExtensionView.as_view(), name="leave-extension-request"),
    path("applications/<int:pk>/resume/", v.SubmitResumptionView.as_view(), name="leave-resume-submit"),
    path("applications/<int:pk>/renominate-substitute/", v.ReNominateSubstituteView.as_view(), name="leave-renominate-substitute"),
    path("substitutes/", v.MySubstituteRequestsView.as_view(), name="leave-substitutes"),
    path("substitutes/<int:pk>/respond/", v.RespondSubstituteRequestView.as_view(), name="leave-substitute-respond"),
    path("approvals/", v.PendingApprovalsQueueView.as_view(), name="leave-approvals-queue"),
    path("approvals/<int:pk>/unit-head-review/", v.UnitHeadReviewView.as_view(), name="leave-unit-head-review"),
    path("approvals/<int:pk>/sanction/", v.SanctionDecisionView.as_view(), name="leave-sanction"),
    path("approvals/<int:pk>/forward/", v.ForwardApprovalView.as_view(), name="leave-forward"),
    path("approvals/<int:pk>/review-cancellation/", v.ReviewCancellationView.as_view(), name="leave-review-cancellation"),
    path("approvals/<int:pk>/review-resumption/", v.ReviewResumptionView.as_view(), name="leave-review-resumption"),
    path("calendar/", v.HolidayCalendarView.as_view(), name="leave-calendar"),
    path("calendar/admin/", v.HolidayCalendarAdminView.as_view(), name="leave-calendar-admin"),
    path("calendar/<int:year>/publish/", v.PublishHolidayCalendarView.as_view(), name="leave-calendar-publish"),
    path("calendar/vacation-periods/", v.VacationPeriodsSyncView.as_view(), name="leave-vacation-periods-sync"),
    path("admin/config/", v.LeaveConfigurationView.as_view(), name="leave-config"),
    path("admin/offline-sync/", v.OfflineLeaveSyncView.as_view(), name="leave-offline-sync"),
    path("admin/applications/<int:pk>/", v.MaintainLeaveRecordView.as_view(), name="leave-record-maintenance"),
]
