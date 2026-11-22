from django.urls import path

from modules.gymkhana.api import views as v

urlpatterns = [
    path("clubs", v.ClubListView.as_view(), name="gymkhana-clubs"),
    path("clubs/create", v.ClubCreateView.as_view(), name="gymkhana-club-create"),
    path("clubs/<int:pk>/approve", v.ClubApproveView.as_view(), name="gymkhana-club-approve"),
    path("clubs/<int:pk>/leadership", v.LeadershipView.as_view(),
         name="gymkhana-club-leadership"),
    path("me/clubs", v.MyClubsView.as_view(), name="gymkhana-my-clubs"),
    path("memberships", v.MembershipListView.as_view(), name="gymkhana-memberships"),
    path("memberships/apply", v.ApplyView.as_view(), name="gymkhana-apply"),
    path("memberships/approve", v.ApproveMembershipsView.as_view(),
         name="gymkhana-memberships-approve"),
    path("venues", v.VenueListView.as_view(), name="gymkhana-venues"),
    path("bookings", v.BookingListView.as_view(), name="gymkhana-bookings"),
    path("sessions", v.SessionCreateView.as_view(), name="gymkhana-sessions"),
    path("events", v.EventCreateView.as_view(), name="gymkhana-events"),
    path("polls", v.OpenPollListView.as_view(), name="gymkhana-polls"),
    path("polls/managed", v.ManagedPollListView.as_view(), name="gymkhana-polls-managed"),
    path("polls/create", v.PollCreateView.as_view(), name="gymkhana-poll-create"),
    path("polls/<int:pk>/votes", v.VoteView.as_view(), name="gymkhana-vote"),
    path("budget-requests", v.BudgetListView.as_view(), name="gymkhana-budget"),
    path("budget-requests/create", v.BudgetCreateView.as_view(),
         name="gymkhana-budget-create"),
    path("event-reports", v.ReportListView.as_view(), name="gymkhana-reports"),
    path("event-reports/create", v.ReportCreateView.as_view(), name="gymkhana-report-create"),
    path("event-reports/<int:pk>", v.ReportDetailView.as_view(), name="gymkhana-report"),
    path("people", v.PeopleSearchView.as_view(), name="gymkhana-people"),
]
