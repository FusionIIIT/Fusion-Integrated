from django.urls import path

from modules.elm.api.views import (
    ELMDataView,
    RequestDecisionView,
    RequestDetailView,
    RequestHistoryView,
    RequestListCreateView,
    RequestWithdrawalView,
    SubstituteNominationView,
    SubstituteResponseView,
)

urlpatterns = [
    path("", ELMDataView.as_view(), name="elm-metadata"),
    path("requests/", RequestListCreateView.as_view(), name="elm-requests"),
    path("requests/history/", RequestHistoryView.as_view(), name="elm-request-history"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="elm-request"),
    path(
        "requests/<int:pk>/withdraw/",
        RequestWithdrawalView.as_view(),
        name="elm-request-withdraw",
    ),
    path(
        "requests/<int:pk>/decision/",
        RequestDecisionView.as_view(),
        name="elm-request-decision",
    ),
    path(
        "requests/<int:pk>/substitute/",
        SubstituteNominationView.as_view(),
        name="elm-substitute-nominate",
    ),
    path(
        "requests/<int:pk>/substitute/respond/",
        SubstituteResponseView.as_view(),
        name="elm-substitute-respond",
    ),
]
