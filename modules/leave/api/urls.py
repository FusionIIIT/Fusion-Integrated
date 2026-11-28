from django.urls import path
from modules.leave.api import views

urlpatterns = [
    path("accounts/", views.LeaveAccountListView.as_view(), name="elm-accounts"),
    path("requests/", views.LeaveRequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>/substitute-action/", views.SubstituteActionView.as_view(), name="elm-substitute-action"),
    path("requests/<int:pk>/unit-head-action/", views.UnitHeadActionView.as_view(), name="elm-unit-head-action"),
    path("requests/<int:pk>/establishment-route/", views.EstablishmentRouteView.as_view(), name="elm-establishment-route"),
    path("requests/<int:pk>/sanction-decision/", views.SanctionActionView.as_view(), name="elm-sanction-decision"),
    path("requests/<int:pk>/withdraw/", views.WithdrawRequestView.as_view(), name="elm-withdraw"),
    path("requests/<int:pk>/resumption/", views.ResumptionActionView.as_view(), name="elm-resumption"),
]
