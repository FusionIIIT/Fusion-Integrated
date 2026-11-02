from django.urls import path

from modules.gymkhana.api.views import (
    ClubListCreateView,
    ClubDetailView,
    ClubConfirmView,
    ClubLeadershipChangeView,
    VenueBookingListCreateView,
    MembershipApplyView,
    MembershipApproveView,
    VotingPollListCreateView,
    CastVoteView,
    BudgetRequestListCreateView,
    EventReportListCreateView,
    FacultyReportReviewView,
)

app_name = "gymkhana"

urlpatterns = [
    path("clubs/", ClubListCreateView.as_view(), name="club-list-create"),
    path("clubs/<int:pk>/", ClubDetailView.as_view(), name="club-detail"),
    path("clubs/<int:pk>/confirm/", ClubConfirmView.as_view(), name="club-confirm"),
    path("clubs/<int:pk>/leadership/", ClubLeadershipChangeView.as_view(), name="club-leadership-change"),
    path("clubs/<int:club_id>/apply/", MembershipApplyView.as_view(), name="membership-apply"),
    path("memberships/<int:pk>/approve/", MembershipApproveView.as_view(), name="membership-approve"),
    path("bookings/", VenueBookingListCreateView.as_view(), name="booking-list-create"),
    path("polls/", VotingPollListCreateView.as_view(), name="poll-list-create"),
    path("polls/<int:poll_id>/vote/", CastVoteView.as_view(), name="cast-vote"),
    path("budgets/", BudgetRequestListCreateView.as_view(), name="budget-list-create"),
    path("reports/", EventReportListCreateView.as_view(), name="report-list-create"),
    path("reports/<int:pk>/review/", FacultyReportReviewView.as_view(), name="faculty-report-review"),
]
