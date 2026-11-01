from django.urls import path

from modules.gymkhana.api import views

urlpatterns = [
    path("clubs/assigned", views.AssignedClubsView.as_view(), name="gymkhana-assigned-clubs"),
    path("clubs", views.ClubListView.as_view(), name="gymkhana-clubs"),
    path("applications/mine", views.MyApplicationsView.as_view(),
         name="gymkhana-my-applications"),
    path("clubs/<int:club_id>/applications",
         views.ClubApplicationsView.as_view(),
         name="gymkhana-club-applications"),
    path("applications/<int:application_id>/review",
         views.ReviewApplicationView.as_view(),
         name="gymkhana-application-review"),
    path("applications/bulk-review", views.BulkReviewView.as_view(),
         name="gymkhana-application-bulk-review"),
]
