from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("requests", v.RequestListCreateView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/related", v.RelatedRequestView.as_view(), name="elm-related-request"),
    path(
        "requests/<int:pk>/transition",
        v.RequestTransitionView.as_view(),
        name="elm-request-transition",
    ),
    path(
        "requests/<int:pk>/substitute-response",
        v.SubstituteResponseView.as_view(),
        name="elm-substitute-response",
    ),
    path("requests/<int:pk>/history", v.HistoryView.as_view(), name="elm-request-history"),
    path("balances/me", v.BalanceView.as_view(), name="elm-balance-me"),
    path("tasks/me", v.MyTasksView.as_view(), name="elm-tasks-me"),
    path("policies", v.PolicyListCreateView.as_view(), name="elm-policies"),
    path("policies/<int:pk>/publish", v.PolicyPublishView.as_view(), name="elm-policy-publish"),
    path("calendars", v.CalendarListCreateView.as_view(), name="elm-calendars"),
    path(
        "calendars/<int:pk>/publish", v.CalendarPublishView.as_view(), name="elm-calendar-publish"
    ),
]
