"""API URL patterns for Gymkhana module."""

from __future__ import annotations

from django.urls import path

from modules.gymkhana.api.views import (
    BookingDetailView,
    BookingListView,
    BudgetDetailView,
    BudgetListView,
    ClubConfirmView,
    ClubDetailView,
    ClubLeadershipView,
    ClubListView,
    EventBookingView,
    MembershipApplyView,
    MembershipApproveView,
    MembershipListView,
    PollDetailView,
    PollListView,
    PollVoteView,
    ReportDetailView,
    ReportListView,
    SessionBookingView,
)

app_name = "gymkhana"

urlpatterns = [
    # Clubs
    path("clubs/", ClubListView.as_view(), name="club-list"),
    path("clubs/<int:pk>/", ClubDetailView.as_view(), name="club-detail"),
    path("clubs/<int:pk>/confirm/", ClubConfirmView.as_view(), name="club-confirm"),
    path("clubs/<int:pk>/leadership/", ClubLeadershipView.as_view(), name="club-leadership"),
    # Bookings
    path("bookings/", BookingListView.as_view(), name="booking-list"),
    path("bookings/session/", SessionBookingView.as_view(), name="booking-session"),
    path("bookings/event/", EventBookingView.as_view(), name="booking-event"),
    path("bookings/<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    # Memberships
    path("memberships/", MembershipListView.as_view(), name="membership-list"),
    path("memberships/apply/", MembershipApplyView.as_view(), name="membership-apply"),
    path(
        "memberships/<int:pk>/approve/", MembershipApproveView.as_view(), name="membership-approve"
    ),
    # Polls
    path("polls/", PollListView.as_view(), name="poll-list"),
    path("polls/<int:pk>/", PollDetailView.as_view(), name="poll-detail"),
    path("polls/<int:pk>/vote/", PollVoteView.as_view(), name="poll-vote"),
    # Budgets
    path("budgets/", BudgetListView.as_view(), name="budget-list"),
    path("budgets/<int:pk>/", BudgetDetailView.as_view(), name="budget-detail"),
    # Reports
    path("reports/", ReportListView.as_view(), name="report-list"),
    path("reports/<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]
