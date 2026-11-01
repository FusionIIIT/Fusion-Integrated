from django.urls import path

from modules.gymkhana import views

urlpatterns = [
    path("clubs", views.ClubListCreateView.as_view(), name="gym-clubs"),
    path("clubs/<int:pk>/approve", views.ClubApproveView.as_view(), name="gym-club-approve"),
    path("memberships", views.MembershipListCreateView.as_view(), name="gym-memberships"),
    path("memberships/<int:pk>/approve", views.MembershipApproveView.as_view(),
         name="gym-membership-approve"),
]
