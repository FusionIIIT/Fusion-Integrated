from django.urls import path
from modules.leave.api import views

app_name = "leave"

urlpatterns = [
    # Applications
    path("applications/", views.LeaveApplicationListCreateView.as_view(), name="application-list-create"),
    path("applications/<int:pk>/", views.LeaveApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/submit/", views.LeaveApplicationSubmitView.as_view(), name="application-submit"),
    path("applications/<int:pk>/withdraw/", views.LeaveApplicationWithdrawView.as_view(), name="application-withdraw"),
    path("applications/<int:pk>/cancel/", views.LeaveApplicationCancelView.as_view(), name="application-cancel"),
    path("applications/<int:pk>/resume/", views.LeaveApplicationResumeView.as_view(), name="application-resume"),

    # Substitute flow
    path("substitute/requests/", views.SubstituteRequestsView.as_view(), name="substitute-requests"),
    path("substitute/<int:pk>/respond/", views.SubstituteRespondView.as_view(), name="substitute-respond"),

    # Reviews & Approvals
    path("reviews/", views.ApprovalQueueView.as_view(), name="approval-queue"),
    path("reviews/<int:pk>/unit-head/", views.UnitHeadReviewView.as_view(), name="unit-head-review"),
    path("reviews/<int:pk>/sanction/", views.SanctionDecisionView.as_view(), name="sanction-decision"),

    # Balances & Calendars
    path("balances/", views.LeaveBalancesView.as_view(), name="balances"),
    path("holidays/", views.HolidayCalendarView.as_view(), name="holidays"),
]
