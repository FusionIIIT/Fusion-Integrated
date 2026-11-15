from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("requests", v.RequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/modify", v.ModifyView.as_view(), name="elm-request-modify"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="elm-request-withdraw"),
    path("requests/<int:pk>/cancel", v.CancelView.as_view(), name="elm-request-cancel"),
    path("requests/<int:pk>/substitute", v.RenominateView.as_view(),
         name="elm-request-substitute"),
    path("requests/<int:pk>/extend", v.ExtendView.as_view(), name="elm-request-extend"),
    path("requests/<int:pk>/resume", v.ResumeView.as_view(), name="elm-request-resume"),
    path("requests/<int:pk>/print", v.PrintView.as_view(), name="elm-request-print"),

    path("balances", v.BalanceView.as_view(), name="elm-balances"),
    path("employees", v.EmployeeSearchView.as_view(), name="elm-employees"),
    path("notifications", v.NotificationListView.as_view(), name="elm-notifications"),

    path("substitutions", v.SubstitutionListView.as_view(), name="elm-substitutions"),
    path("substitutions/<int:pk>/respond", v.SubstitutionRespondView.as_view(),
         name="elm-substitution-respond"),

    path("queue", v.QueueView.as_view(), name="elm-queue"),
    path("queue/<int:pk>/decide", v.DecideView.as_view(), name="elm-decide"),
    path("resumptions", v.ResumptionQueueView.as_view(), name="elm-resumptions"),
    path("resumptions/<int:pk>/verify", v.VerifyView.as_view(), name="elm-verify"),

    path("admin/policies", v.PolicyListView.as_view(), name="elm-policies"),
    path("admin/policies/<int:pk>", v.PolicyDetailView.as_view(), name="elm-policy"),
    path("admin/policies/<int:pk>/publish", v.PolicyPublishView.as_view(),
         name="elm-policy-publish"),
    path("admin/calendars", v.CalendarListView.as_view(), name="elm-calendars"),
    path("admin/calendars/<int:pk>", v.CalendarDetailView.as_view(), name="elm-calendar"),
    path("admin/calendars/<int:pk>/publish", v.CalendarPublishView.as_view(),
         name="elm-calendar-publish"),
    path("admin/offline", v.OfflineListView.as_view(), name="elm-offline"),
    path("admin/accounts", v.AccountView.as_view(), name="elm-account"),
]
