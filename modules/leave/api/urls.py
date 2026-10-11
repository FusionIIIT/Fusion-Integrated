"""
URL patterns for the Leave Management API.
Maps HTTP methods and paths to DRF views.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from modules.leave.api.views import (
    MyApplicationsView,
    ApplyLeaveView,
    ApplicationDetailView,
    WithdrawApplicationView,
    CancelApprovedLeaveView,
    ExtendLeaveView,
    SubmitResumptionView,
    RespondToSubstituteView,
    NominateReplacementSubstituteView,
    ApprovalsInboxView,
    UnitHeadDecisionView,
    UnitHeadRecommendationView,
    EstablishmentVerifyAndRouteView,
    FinalSanctionDecisionView,
    DecideCancellationView,
    BalancesView,
    HistoryView,
    ReviewResumptionView,
)

# Router for generic CRUD if needed in future, though we use specific views here.
router = DefaultRouter()

urlpatterns = [
    # Application Management
    path("my-applications/", MyApplicationsView.as_view(), name="my-applications-list"),
    path("apply/", ApplyLeaveView.as_view(), name="apply-leave"),
    
    # Single Application Detail (used by all actions)
    path("<int:pk>/", ApplicationDetailView.as_view(), name="application-detail"),
    
    # Lifecycle Actions on Application
    path("<int:pk>/withdraw/", WithdrawApplicationView.as_view(), name="withdraw-application"),
    path("<int:pk>/cancel/", CancelApprovedLeaveView.as_view(), name="cancel-approved-leave"),
    path("<int:pk>/extend/", ExtendLeaveView.as_view(), name="extend-leave"),
    path("<int:pk>/resumption-submit/", SubmitResumptionView.as_view(), name="submit-resumption"),
    path("<int:pk>/substitute/respond/", RespondToSubstituteView.as_view(), name="respond-to-substitute"),
    path("<int:pk>/substitute/nominate-replacement/", NominateReplacementSubstituteView.as_view(), name="nominate-replacement-substitute"),
    
    # Decision Actions (Inbox and specific decisions)
    path("approvals-inbox/", ApprovalsInboxView.as_view(), name="approvals-inbox-list"),
    path("<int:pk>/decide-unit-head/", UnitHeadDecisionView.as_view(), name="unit-head-decision"),
    path("<int:pk>/decide-recommendation/", UnitHeadRecommendationView.as_view(), name="unit-head-recommendation"),
    path("<int:pk>/establishment-route/", EstablishmentVerifyAndRouteView.as_view(), name="establishment-route"),
    path("<int:pk>/final-sanction/", FinalSanctionDecisionView.as_view(), name="final-sanction-decision"),
    path("<int:pk>/decide-cancellation/", DecideCancellationView.as_view(), name="decide-cancellation"),
    
    # Resumption Review (Specific to resumption applications)
    path("<int:pk>/resumption-review/", ReviewResumptionView.as_view(), name="review-resumption"),
    
    # Balances and History
    path("balances/<int:year>/", BalancesView.as_view(), name="user-balances"),
    path("history/", HistoryView.as_view(), name="user-history"),
]
