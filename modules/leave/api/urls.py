from django.urls import path

from modules.leave.api import admin_views as a
from modules.leave.api import views as v

urlpatterns = [
    # requests
    path("requests", v.RequestListView.as_view(), name="leave-requests"),
    path(
        "requests/<int:pk>/withdraw", v.RequestWithdrawView.as_view(), name="leave-request-withdraw"
    ),
    path("requests/<int:pk>/cancel", v.RequestCancelView.as_view(), name="leave-request-cancel"),
    path(
        "requests/<int:pk>/substitute-response",
        v.SubstituteResponseView.as_view(),
        name="leave-request-substitute-response",
    ),
    path("requests/<int:pk>/review", v.RequestReviewView.as_view(), name="leave-request-review"),
    path("requests/<int:pk>/route", v.RequestRouteView.as_view(), name="leave-request-route"),
    path(
        "requests/<int:pk>/sanction", v.RequestSanctionView.as_view(), name="leave-request-sanction"
    ),
    path(
        "requests/<int:pk>/resumption",
        v.ResumptionSubmitView.as_view(),
        name="leave-request-resumption",
    ),
    # resumptions
    path("resumptions", a.ResumptionListView.as_view(), name="leave-resumptions"),
    path(
        "resumptions/<int:pk>/review",
        a.ResumptionReviewView.as_view(),
        name="leave-resumption-review",
    ),
    # balances
    path("balances", a.BalanceListView.as_view(), name="leave-balances"),
    # policies
    path("policies", a.PolicyListView.as_view(), name="leave-policies"),
    path("policies", a.PolicyListView.as_view(), name="leave-policies"),
    path("policies", a.PolicyListView.as_view(), name="leave-policies"),
    # units
    path("units", a.UnitListView.as_view(), name="leave-units"),
    path("units", a.UnitListView.as_view(), name="leave-units"),
    path("units", a.UnitListView.as_view(), name="leave-units"),
    # holidays
    path("holidays", a.HolidayListView.as_view(), name="leave-holidays"),
    path("holidays", a.HolidayListView.as_view(), name="leave-holidays"),
    path("holidays", a.HolidayListView.as_view(), name="leave-holidays"),
    # offline-records
    path("offline-records", a.OfflineRecordView.as_view(), name="leave-offline-records"),
]
