from django.urls import path

from modules.gymkhana.api import views

urlpatterns = [
    path("clubs/", views.ClubListCreateView.as_view(), name="club_list_create"),
    path("clubs/<int:pk>/", views.ClubDetailView.as_view(), name="club_detail"),
    path("clubs/<int:pk>/confirm/", views.ClubConfirmView.as_view(), name="club_confirm"),
    path(
        "clubs/<int:pk>/leadership/",
        views.ClubLeadershipChangeView.as_view(),
        name="club_leadership_change",
    ),
    path(
        "clubs/<int:pk>/sessions/",
        views.ClubSessionBookingView.as_view(),
        name="club_session_booking",
    ),
    path(
        "clubs/<int:pk>/events/",
        views.ClubEventBookingView.as_view(),
        name="club_event_booking",
    ),
    path(
        "clubs/<int:pk>/bookings/",
        views.ClubBookingListView.as_view(),
        name="club_booking_list",
    ),
    path(
        "clubs/<int:pk>/memberships/",
        views.ClubMembershipListView.as_view(),
        name="club_membership_list",
    ),
    path(
        "clubs/<int:pk>/memberships/apply/",
        views.ClubMembershipApplyView.as_view(),
        name="club_membership_apply",
    ),
    path(
        "memberships/<int:pk>/approve/",
        views.MembershipApproveView.as_view(),
        name="membership_approve",
    ),
    path(
        "clubs/<int:pk>/polls/",
        views.ClubPollCreateView.as_view(),
        name="club_poll_create",
    ),
    path("polls/", views.ActivePollListView.as_view(), name="active_poll_list"),
    path("polls/<int:pk>/vote/", views.PollVoteView.as_view(), name="poll_vote"),
    path(
        "clubs/<int:pk>/budgets/",
        views.ClubBudgetRequestView.as_view(),
        name="club_budget_request",
    ),
    path(
        "clubs/<int:pk>/reports/",
        views.ClubEventReportReviewView.as_view(),
        name="club_event_report_review",
    ),
    path(
        "clubs/<int:pk>/reports/submit/",
        views.ClubEventReportSubmitView.as_view(),
        name="club_event_report_submit",
    ),
    path(
        "bookings/<int:pk>/poster/",
        views.ClubBookingPosterDownloadView.as_view(),
        name="club_booking_poster_download",
    ),
    path(
        "budgets/<int:pk>/file/",
        views.ClubBudgetFileDownloadView.as_view(),
        name="club_budget_file_download",
    ),
    path(
        "reports/<int:pk>/file/",
        views.ClubEventReportFileDownloadView.as_view(),
        name="club_event_report_file_download",
    ),
]
