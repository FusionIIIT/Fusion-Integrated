from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("categories", v.CategoryListView.as_view(), name="elm-categories"),
    path("balances", v.BalanceListView.as_view(), name="elm-balances"),
    path("applications", v.ApplicationListCreateView.as_view(), name="elm-applications"),
    path("applications/apply", v.ApplicationListCreateView.as_view(), name="elm-apply"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(), name="elm-application-detail"),
    path(
        "applications/<int:pk>/transition",
        v.ApplicationTransitionView.as_view(),
        name="elm-application-transition",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.ApplicationWithdrawView.as_view(),
        name="elm-application-withdraw",
    ),
    path(
        "applications/<int:pk>/substitute",
        v.SubstituteResponseView.as_view(),
        name="elm-substitute-response",
    ),
    path("approvals", v.PendingApprovalsListView.as_view(), name="elm-approvals"),
]
