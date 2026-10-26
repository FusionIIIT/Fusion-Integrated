"""URL routing configuration for ELM API endpoints."""
from django.urls import path

from modules.elm.api import views

app_name = "elm"

urlpatterns = [
    # Employee: own leaves
    path("leaves/", views.MyLeavesView.as_view(), name="my-leaves"),
    path("leaves/<int:pk>/", views.LeaveDetailWithdrawView.as_view(), name="leave-detail"),
    path("leaves/<int:pk>/cancel/", views.LeaveCancellationView.as_view(), name="leave-cancel"),
    path("leaves/<int:pk>/resume/", views.LeaveResumptionView.as_view(), name="leave-resume"),

    # Balances & Holidays
    path("balances/", views.MyBalancesView.as_view(), name="my-balances"),
    path("holidays/", views.HolidayCalendarView.as_view(), name="holidays"),

    # Workflow: substitute
    path("substitute/", views.SubstituteQueueView.as_view(), name="substitute-queue"),
    path("substitute/<int:pk>/respond/", views.SubstituteRespondView.as_view(), name="substitute-respond"),

    # Workflow: unit head
    path("unit-head/", views.UnitHeadQueueView.as_view(), name="unit-head-queue"),
    path("unit-head/<int:pk>/review/", views.UnitHeadReviewView.as_view(), name="unit-head-review"),

    # Workflow: sanction authority
    path("sanctions/", views.SanctionQueueView.as_view(), name="sanctions-queue"),
    path("sanctions/<int:pk>/sanction/", views.SanctionDecisionView.as_view(), name="sanction-decision"),
]
