from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("types", v.LeaveTypeListView.as_view(), name="elm-types"),
    path("types/create", v.LeaveTypeCreateView.as_view(), name="elm-type-create"),
    path("types/<int:pk>/<str:action>", v.LeaveTypeStatusView.as_view(),
         name="elm-type-status"),

    path("holidays", v.HolidayListView.as_view(), name="elm-holidays"),
    path("holidays/create", v.HolidayCreateView.as_view(),
         name="elm-holiday-create"),
    path("holidays/<int:pk>", v.HolidayDeleteView.as_view(), name="elm-holiday"),

    path("applications", v.ApplicationListView.as_view(),
         name="elm-applications"),
    path("applications/submit", v.ApplicationSubmitView.as_view(),
         name="elm-application-submit"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(),
         name="elm-application"),
    path("applications/<int:pk>/transition",
         v.ApplicationTransitionView.as_view(),
         name="elm-application-transition"),
    path("applications/<int:pk>/history", v.ApplicationHistoryView.as_view(),
         name="elm-application-history"),

    path("approvals", v.ApprovalsInboxView.as_view(), name="elm-approvals"),

    path("balances", v.BalanceListView.as_view(), name="elm-balances"),
    path("balances/grant", v.BalanceGrantView.as_view(),
         name="elm-balance-grant"),
]
