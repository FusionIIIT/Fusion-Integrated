"""URL routing for Employee Leave Management (ELM).

Maintains complete backward compatibility with Phase 1 paths while exposing
full Phase 2 lifecycle, substitute, review, sanction, balance, and inbox endpoints.
"""
from django.urls import path

from .views import (
    CancellationSanctionView,
    CancellationUnitHeadReviewView,
    HolidayCalendarListView,
    HolidayCalendarPublishView,
    LeaveBalanceListView,
    LeaveRequestApproveView,
    LeaveRequestCancelView,
    LeaveRequestCreateView,
    LeaveRequestDetailView,
    LeaveRequestListCreateView,
    LeaveRequestListView,
    LeaveRequestRejectView,
    LeaveRequestWithdrawView,
    NominateReplacementSubstituteView,
    OfflineSanctionView,
    PendingApprovalsInboxView,
    RequestCancellationView,
    SanctionDecisionView,
    SubstituteResponseView,
    UnitHeadReviewView,
    YearEndRolloverView,
)

urlpatterns = [
    # Core Application & Retrieval (EL-UC-001)
    path("leave-requests/", LeaveRequestListCreateView.as_view(), name="leave-request-list-create"),
    path("leave-requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),

    # Lifecycle Operations
    path("leave-requests/<int:pk>/withdraw/", LeaveRequestWithdrawView.as_view(), name="leave-request-withdraw"),
    path("leave-requests/<int:pk>/substitute-respond/", SubstituteResponseView.as_view(), name="substitute-respond"),
    path("leave-requests/<int:pk>/nominate-replacement-substitute/", NominateReplacementSubstituteView.as_view(), name="nominate-replacement-substitute"),
    path("leave-requests/<int:pk>/unit-head-review/", UnitHeadReviewView.as_view(), name="unit-head-review"),
    path("leave-requests/<int:pk>/sanction/", SanctionDecisionView.as_view(), name="sanction-decision"),

    # Cancellation Operations (EL-UC-008, CW-EL-02)
    path("leave-requests/<int:pk>/request-cancellation/", RequestCancellationView.as_view(), name="request-cancellation"),
    path("leave-requests/<int:pk>/cancellation-unit-head-review/", CancellationUnitHeadReviewView.as_view(), name="cancellation-unit-head-review"),
    path("leave-requests/<int:pk>/sanction-cancellation/", CancellationSanctionView.as_view(), name="sanction-cancellation"),

    # Balance, Inbox & Calendars (EL-UC-012, EL-UC-015)
    path("balances/", LeaveBalanceListView.as_view(), name="leave-balance-list"),
    path("inbox/pending/", PendingApprovalsInboxView.as_view(), name="pending-approvals-inbox"),
    path("holidays/", HolidayCalendarListView.as_view(), name="holiday-list"),

    # Administrative Actions (EL-UC-015, EL-UC-016, EL-UC-020)
    path("holidays/publish/", HolidayCalendarPublishView.as_view(), name="holiday-calendar-publish"),
    path("admin/rollover/", YearEndRolloverView.as_view(), name="admin-rollover"),
    path("admin/offline-sanction/", OfflineSanctionView.as_view(), name="admin-offline-sanction"),

    # Phase 1 Legacy Compatibility Aliases
    path("leave-requests/create/", LeaveRequestCreateView.as_view(), name="leave-request-create"),
    path("leave-requests/<int:pk>/approve/", LeaveRequestApproveView.as_view(), name="leave-request-approve"),
    path("leave-requests/<int:pk>/reject/", LeaveRequestRejectView.as_view(), name="leave-request-reject"),
    path("leave-requests/<int:pk>/cancel/", LeaveRequestCancelView.as_view(), name="leave-request-cancel"),
]
