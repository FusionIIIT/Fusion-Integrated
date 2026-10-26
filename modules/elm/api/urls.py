from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    # Applications (list, create, detail, withdraw, cancel, extend, resume)
    path("applications", v.LeaveApplicationListCreateView.as_view(), name="elm-leave-applications"),
    path("applications/<int:pk>", v.LeaveApplicationDetailView.as_view(), name="elm-leave-detail"),
    path(
        "applications/<int:pk>/withdraw",
        v.LeaveApplicationWithdrawView.as_view(),
        name="elm-leave-withdraw",
    ),
    path(
        "applications/<int:pk>/cancel",
        v.LeaveApplicationCancelView.as_view(),
        name="elm-leave-cancel",
    ),
    path(
        "applications/<int:pk>/extend",
        v.LeaveApplicationExtendView.as_view(),
        name="elm-leave-extend",
    ),
    path(
        "applications/<int:pk>/resume",
        v.LeaveApplicationResumeView.as_view(),
        name="elm-leave-resume",
    ),
    # Substitute actions
    path(
        "substitute/pending", v.SubstitutePendingListView.as_view(), name="elm-substitute-pending"
    ),
    path(
        "applications/<int:pk>/substitute-respond",
        v.SubstituteRespondView.as_view(),
        name="elm-substitute-respond",
    ),
    path(
        "applications/<int:pk>/substitute-replace",
        v.SubstituteReplacementView.as_view(),
        name="elm-substitute-replace",
    ),
    # Unit Head review
    path("unit-head/pending", v.UnitHeadPendingListView.as_view(), name="elm-unit-head-pending"),
    path(
        "applications/<int:pk>/unit-head-review",
        v.UnitHeadReviewActionView.as_view(),
        name="elm-unit-head-review",
    ),
    # Establishment routing
    path(
        "establishment/pending",
        v.EstablishmentPendingListView.as_view(),
        name="elm-establishment-pending",
    ),
    path(
        "applications/<int:pk>/establishment-route",
        v.EstablishmentRouteActionView.as_view(),
        name="elm-establishment-route",
    ),
    # Sanctioning decision
    path("sanctions/pending", v.SanctionPendingListView.as_view(), name="elm-sanctions-pending"),
    path(
        "applications/<int:pk>/sanction", v.SanctionActionView.as_view(), name="elm-sanction-action"
    ),
    path(
        "applications/<int:pk>/resumption-review",
        v.ResumptionReviewActionView.as_view(),
        name="elm-resumption-review",
    ),
    # Balances & Holiday Calendar
    path("balances", v.LeaveBalanceListView.as_view(), name="elm-balances"),
    path("calendar", v.HolidayCalendarListView.as_view(), name="elm-calendar"),
]
