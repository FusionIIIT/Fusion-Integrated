from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("requests", v.LeaveRequestListView.as_view(), name="elm-requests"),
    path("requests/apply", v.ApplyView.as_view(), name="elm-apply"),
    path("requests/<int:pk>", v.LeaveRequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/transition", v.TransitionView.as_view(),
         name="elm-request-transition"),
    path("balances", v.BalanceView.as_view(), name="elm-balances"),
]
