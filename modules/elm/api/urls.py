"""URL configuration for ELM API endpoints."""
from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("leaves/", views.MyLeavesView.as_view(), name="elm-my-leaves"),
    path("leaves/<int:pk>/", views.LeaveDetailWithdrawView.as_view(), name="elm-leave-detail-withdraw"),
    path("leaves/<int:pk>/cancel/", views.LeaveCancellationView.as_view(), name="elm-leave-cancel"),
    path("leaves/<int:pk>/resume/", views.LeaveResumptionView.as_view(), name="elm-leave-resume"),
    path("leaves/<int:pk>/extend/", views.LeaveExtensionView.as_view(), name="elm-leave-extend"),
    path(
        "leaves/<int:pk>/extension-substitute/",
        views.ExtensionSubstituteView.as_view(),
        name="elm-extension-substitute",
    ),
    path("balances/", views.MyBalancesView.as_view(), name="elm-my-balances"),
    path("substitute/", views.SubstituteQueueView.as_view(), name="elm-substitute-queue"),
    path("substitute/<int:pk>/", views.SubstituteQueueView.as_view(), name="elm-substitute-respond"),
    path("unit-head/", views.UnitHeadReviewView.as_view(), name="elm-unit-head-queue"),
    path("unit-head/<int:pk>/", views.UnitHeadReviewView.as_view(), name="elm-unit-head-review"),
    path("sanctions/", views.SanctionDecisionView.as_view(), name="elm-sanctions-queue"),
    path("sanctions/<int:pk>/", views.SanctionDecisionView.as_view(), name="elm-sanctions-decide"),
    path("holidays/", views.HolidayCalendarView.as_view(), name="elm-holidays"),
]
