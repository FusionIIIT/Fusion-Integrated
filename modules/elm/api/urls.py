from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("balances", v.LeaveBalanceListView.as_view(), name="elm-balances"),
    path(
        "applications",
        v.LeaveApplicationListCreateView.as_view(),
        name="elm-applications",
    ),
]
