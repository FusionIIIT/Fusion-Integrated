from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    # requests
    path("requests", v.RequestListView.as_view(), name="elm-requests"),
    path("requests/export.csv", v.RequestsExportView.as_view(),
         name="elm-requests-export"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="elm-request-withdraw"),
    path("requests/<int:pk>/cancel", v.CancelView.as_view(),
         name="elm-request-cancel"),
    path("requests/<int:pk>/extend", v.ExtendView.as_view(),
         name="elm-request-extend"),
    path("requests/<int:pk>/nominate", v.NominateView.as_view(),
         name="elm-request-nominate"),
    path("requests/<int:pk>/resumption", v.ResumptionSubmitView.as_view(),
         name="elm-request-resumption"),

    # approval chain
    path("requests/<int:pk>/review", v.UnitHeadReviewView.as_view(),
         name="elm-request-review"),
    path("requests/<int:pk>/establishment", v.EstablishmentView.as_view(),
         name="elm-request-establishment"),
    path("requests/<int:pk>/sanction", v.SanctionView.as_view(),
         name="elm-request-sanction"),
    path("resumptions/<int:pk>/review", v.ResumptionReviewView.as_view(),
         name="elm-resumption-review"),

    # tasks and substitutions
    path("tasks", v.TaskQueueView.as_view(), name="elm-tasks"),
    path("substitutions", v.SubstitutionListView.as_view(),
         name="elm-substitutions"),
    path("substitutions/<int:pk>/respond", v.SubstitutionRespondView.as_view(),
         name="elm-substitution-respond"),

    # accounts
    path("accounts", v.AccountListView.as_view(), name="elm-accounts"),
    path("accounts/ledger", v.LedgerListView.as_view(), name="elm-ledger"),

    # policy
    path("policy", v.PolicyView.as_view(), name="elm-policy"),
    path("policy/<str:category>", v.PolicyView.as_view(), name="elm-policy-type"),
    path("policy/year-end", v.YearEndView.as_view(), name="elm-year-end"),

    # calendar
    path("calendars", v.CalendarListView.as_view(), name="elm-calendars"),
    path("calendars/<int:pk>/holidays", v.CalendarHolidayView.as_view(),
         name="elm-calendar-holidays"),
    path("calendars/<int:pk>/publish", v.CalendarPublishView.as_view(),
         name="elm-calendar-publish"),
    path("vacations", v.VacationListView.as_view(), name="elm-vacations"),

    # records
    path("records", v.RecordListView.as_view(), name="elm-records"),
    path("records/offline", v.OfflineRecordView.as_view(),
         name="elm-offline-record"),

    # SLA
    path("sla", v.SlaListView.as_view(), name="elm-sla"),
    path("sla/process", v.SlaProcessView.as_view(), name="elm-sla-process"),
    path("sla/<str:task_type>", v.SlaUpdateView.as_view(), name="elm-sla-type"),
]
