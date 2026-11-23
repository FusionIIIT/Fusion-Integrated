"""API URL patterns for Gymkhana module."""

from __future__ import annotations

from django.urls import path

from modules.gymkhana.api.views import (
    AccessView,
    BookingDetailView,
    BookingListView,
    BookingPosterView,
    BudgetDetailView,
    BudgetFileView,
    BudgetListView,
    ClubConfirmView,
    ClubDetailView,
    ClubLeadershipView,
    ClubListView,
    EventBookingView,
    MembershipApplyView,
    MembershipApproveView,
    MembershipListView,
    PeopleSearchView,
    PollDetailView,
    PollListView,
    PollOptionsView,
    PollVoteView,
    ReportDetailView,
    ReportFileView,
    ReportListView,
    SessionBookingView,
    VenueListView,
)

app_name = "gymkhana"

urlpatterns = [
    path("access/", AccessView.as_view(), name="access"),
    path("venues/", VenueListView.as_view(), name="venue-list"),
    path("people/", PeopleSearchView.as_view(), name="people-search"),
    path("poll-options/", PollOptionsView.as_view(), name="poll-options"),
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
    path("bookings/<int:pk>/poster/", BookingPosterView.as_view(), name="booking-poster"),
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
    path("budgets/<int:pk>/file/", BudgetFileView.as_view(), name="budget-file"),
    # Reports
    path("reports/", ReportListView.as_view(), name="report-list"),
    path("reports/<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("reports/<int:pk>/file/", ReportFileView.as_view(), name="report-file"),
]
