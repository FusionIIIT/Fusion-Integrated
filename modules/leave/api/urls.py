"""URL routes for Employee Leave Management REST API."""
from django.urls import path

from modules.leave.api.views import (
    HolidayCalendarListView,
    LeaveApplicationCancellationReviewView,
    LeaveApplicationCancelView,
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
    LeaveApplicationResumptionReviewView,
    LeaveApplicationResumptionView,
    LeaveApplicationReviewView,
    LeaveApplicationWithdrawView,
    LeaveBalanceListView,
    LeaveTypeListView,
    ReplacementSubstituteView,
    SubstituteResponseView,
)

urlpatterns = [
    path("types/", LeaveTypeListView.as_view(), name="leave-types"),
    path("calendar/", HolidayCalendarListView.as_view(), name="leave-calendar"),
    path("balances/", LeaveBalanceListView.as_view(), name="leave-balances"),
    path(
        "applications/",
        LeaveApplicationListCreateView.as_view(),
        name="leave-applications",
    ),
    path(
        "applications/<int:pk>/",
        LeaveApplicationDetailView.as_view(),
        name="leave-application-detail",
    ),
    path(
        "applications/<int:pk>/substitute/",
        SubstituteResponseView.as_view(),
        name="leave-substitute-response",
    ),
    path(
        "applications/<int:pk>/replacement-substitute/",
        ReplacementSubstituteView.as_view(),
        name="leave-replacement-substitute",
    ),
    path(
        "applications/<int:pk>/review/",
        LeaveApplicationReviewView.as_view(),
        name="leave-application-review",
    ),
    path(
        "applications/<int:pk>/withdraw/",
        LeaveApplicationWithdrawView.as_view(),
        name="leave-application-withdraw",
    ),
    path(
        "applications/<int:pk>/cancel/",
        LeaveApplicationCancelView.as_view(),
        name="leave-application-cancel",
    ),
    path(
        "applications/<int:pk>/cancellation-review/",
        LeaveApplicationCancellationReviewView.as_view(),
        name="leave-cancellation-review",
    ),
    path(
        "applications/<int:pk>/resumption/",
        LeaveApplicationResumptionView.as_view(),
        name="leave-application-resumption",
    ),
    path(
        "applications/<int:pk>/resumption-review/",
        LeaveApplicationResumptionReviewView.as_view(),
        name="leave-resumption-review",
    ),
]
