from django.urls import path

from modules.elm.api.views import (
    AdminBalanceView, AdminCalendarView, AdminRouteView, DecideView,
    LeaveTypesView, MyApplicationsView, MyBalanceView, PendingApprovalsView,
    WithdrawView,
)

urlpatterns = [
    path("types", LeaveTypesView.as_view(), name="elm-leave-types"),
    path("applications", MyApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/withdraw", WithdrawView.as_view(), name="elm-withdraw"),
    path("applications/pending", PendingApprovalsView.as_view(), name="elm-pending-approvals"),
    path("applications/<int:pk>/decide", DecideView.as_view(), name="elm-decide"),
    path("balance", MyBalanceView.as_view(), name="elm-balance"),
    path("admin/balances", AdminBalanceView.as_view(), name="elm-admin-balance"),
    path("admin/routes/<int:employee_id>/<str:category>", AdminRouteView.as_view(),
         name="elm-admin-route"),
    path("admin/calendar", AdminCalendarView.as_view(), name="elm-admin-calendar"),
]
