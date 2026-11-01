"""URL patterns for Employee Leave Management (ELM) API."""
from django.urls import path
from modules.leave.api import views

app_name = "leave"

urlpatterns = [
    # Employee self-service
    path("apply/", views.ApplyLeaveView.as_view(), name="apply"),
    path("mine/", views.MyLeavesView.as_view(), name="mine"),
    path("balances/", views.MyBalancesView.as_view(), name="balances"),
    path("<int:request_id>/", views.LeaveDetailView.as_view(), name="detail"),
    path("<int:request_id>/withdraw/", views.WithdrawLeaveView.as_view(), name="withdraw"),
    path("<int:request_id>/cancel/", views.CancelLeaveView.as_view(), name="cancel"),
    path("<int:request_id>/extend/", views.ExtendLeaveView.as_view(), name="extend"),
    path("<int:request_id>/resume/", views.ResumptionLeaveView.as_view(), name="resume"),
    path("<int:request_id>/print/", views.PrintLeaveApplicationView.as_view(), name="print"),

    # Substitute workflow
    path("substitute/", views.SubstituteInboxView.as_view(), name="substitute-inbox"),
    path("substitute/<int:request_id>/respond/", views.SubstituteRespondView.as_view(), name="substitute-respond"),
    path("substitute/<int:request_id>/replace/", views.ReplaceSubstituteView.as_view(), name="substitute-replace"),

    # Approvals workflow
    path("approvals/", views.ApprovalsInboxView.as_view(), name="approvals-inbox"),
    path("approvals/<int:request_id>/unit-head/", views.UnitHeadReviewView.as_view(), name="unit-head-review"),
    path("approvals/<int:request_id>/sanction/", views.SanctionDecisionView.as_view(), name="sanction-decision"),
    path("approvals/<int:request_id>/resumption/", views.ReviewResumptionView.as_view(), name="resumption-review"),

    # Calendars & references
    path("calendar/", views.HolidayCalendarView.as_view(), name="calendar"),
    path("vacation-periods/", views.VacationPeriodView.as_view(), name="vacation-periods"),

    # Administration
    path("admin/offline-sync/", views.OfflineLeaveSyncView.as_view(), name="offline-sync"),
    path("admin/year-end/", views.YearEndProcessingView.as_view(), name="year-end"),
]
