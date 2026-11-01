from django.urls import path

from modules.elm.api import views as elm_views

urlpatterns = [
    # Leave applications
    path("applications", elm_views.LeaveApplicationListView.as_view(),
         name="elm-application-list"),
    path("applications/apply", elm_views.LeaveApplicationCreateView.as_view(),
         name="elm-apply"),
    path("applications/<int:pk>/transition",
         elm_views.LeaveApplicationTransitionView.as_view(),
         name="elm-application-transition"),
    path("applications/<int:pk>/history",
         elm_views.LeaveApplicationHistoryView.as_view(),
         name="elm-application-history"),
    path("applications/bulk-transition",
         elm_views.LeaveApplicationBulkTransitionView.as_view(),
         name="elm-application-bulk-transition"),

    # Leave balance
    path("balance", elm_views.EmployeeLeaveBalanceListView.as_view(),
         name="elm-balance"),

    # Leave status/history
    path("history", elm_views.LeaveHistoryListView.as_view(),
         name="elm-history"),

    # Substitute nominations
    path("substitutes", elm_views.SubstituteNominationListView.as_view(),
         name="elm-substitute-list"),
    path("substitutes/<int:pk>/accept",
         elm_views.SubstituteAcceptView.as_view(),
         name="elm-substitute-accept"),

    # SLA thresholds
    path("sla", elm_views.SLAStatusView.as_view(),
         name="elm-sla-status"),

    # Year-end processing
    path("year-end", elm_views.YearEndProcessingView.as_view(),
         name="elm-year-end"),
]