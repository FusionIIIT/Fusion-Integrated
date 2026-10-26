from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("balances", v.LeaveBalanceListView.as_view(), name="elm-balances"),
    path(
        "applications",
        v.LeaveApplicationListCreateView.as_view(),
        name="elm-applications",
    ),
    path(
        "nominations/<int:pk>/respond",
        v.SubstituteResponseView.as_view(),
        name="elm-nomination-respond",
    ),
    path(
        "applications/<int:pk>/review",
        v.LeaveApplicationReviewView.as_view(),
        name="elm-application-review",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.LeaveApplicationWithdrawView.as_view(),
        name="elm-application-withdraw",
    ),
]
