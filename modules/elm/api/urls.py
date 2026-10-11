from django.urls import path
from modules.elm.api import views as v

urlpatterns = [
    path("balances", v.MyBalancesView.as_view(), name="elm-balances"),
    path("applications", v.ApplicationListView.as_view(), name="elm-applications"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(), name="elm-application-detail"),
    path("applications/<int:pk>/cancel", v.CancelApplicationView.as_view(), name="elm-application-cancel"),
    path("approvals/pending", v.PendingApprovalsView.as_view(), name="elm-approvals-pending"),
    path("approvals/<int:pk>/review", v.ReviewApplicationView.as_view(), name="elm-application-review"),
    path("approvals/<int:pk>/sanction", v.SanctionApplicationView.as_view(), name="elm-application-sanction"),
    path("holidays", v.HolidayListView.as_view(), name="elm-holidays"),
]
