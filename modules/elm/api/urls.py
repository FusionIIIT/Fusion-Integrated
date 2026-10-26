from django.urls import path
from modules.elm.api import views

urlpatterns = [
    path("balances", views.MyLeaveBalancesView.as_view(), name="elm-balances"),
    path("requests", views.LeaveRequestListCreateView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", views.LeaveRequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/actions", views.LeaveRequestDecisionView.as_view(),
         name="elm-request-action"),
]
