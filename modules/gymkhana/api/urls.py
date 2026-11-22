"""URL patterns for Gymkhana API (Blueprint §3.5)."""
from django.urls import re_path

from modules.gymkhana.api import views as v

urlpatterns = [
    # Clubs & Leadership
    re_path(r"^clubs/?$", v.ClubListView.as_view(), name="gymkhana-club-list"),
    re_path(r"^clubs/(?P<pk>\d+)/?$", v.ClubDetailView.as_view(), name="gymkhana-club-detail"),
    re_path(r"^clubs/(?P<pk>\d+)/approve/?$", v.ClubApproveView.as_view(), name="gymkhana-club-approve"),
    re_path(r"^clubs/(?P<pk>\d+)/leadership/?$", v.ClubLeadershipView.as_view(), name="gymkhana-club-leadership"),

    # Memberships
    re_path(r"^memberships/?$", v.MembershipListView.as_view(), name="gymkhana-membership-list"),
    re_path(r"^clubs/(?P<pk>\d+)/memberships/?$", v.ClubMembershipListView.as_view(), name="gymkhana-club-memberships"),
    re_path(r"^memberships/(?P<pk>\d+)/approve/?$", v.MembershipApproveView.as_view(), name="gymkhana-membership-approve"),

    # Bookings
    re_path(r"^bookings/?$", v.BookingListView.as_view(), name="gymkhana-booking-list"),
    re_path(r"^sessions/?$", v.SessionBookingView.as_view(), name="gymkhana-session-create"),
    re_path(r"^events/?$", v.EventBookingView.as_view(), name="gymkhana-event-create"),

    # Polls & Voting
    re_path(r"^polls/?$", v.PollListView.as_view(), name="gymkhana-poll-list"),
    re_path(r"^polls/(?P<pk>\d+)/?$", v.PollDetailView.as_view(), name="gymkhana-poll-detail"),
    re_path(r"^polls/(?P<pk>\d+)/vote/?$", v.PollVoteView.as_view(), name="gymkhana-poll-vote"),

    # Budgets
    re_path(r"^clubs/(?P<pk>\d+)/budgets/?$", v.ClubBudgetListView.as_view(), name="gymkhana-club-budgets"),

    # Event Reports
    re_path(r"^clubs/(?P<pk>\d+)/reports/?$", v.ClubReportListView.as_view(), name="gymkhana-club-reports"),
    re_path(r"^reports/(?P<pk>\d+)/?$", v.EventReportDetailView.as_view(), name="gymkhana-report-detail"),
    re_path(r"^reports/(?P<pk>\d+)/download/?$", v.EventReportDownloadView.as_view(), name="gymkhana-report-download"),
]
