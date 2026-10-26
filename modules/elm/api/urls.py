from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("applications", v.LeaveListCreateView.as_view(), name="elm-applications"),
    path("applications/<int:pk>", v.LeaveDetailView.as_view(), name="elm-application"),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="elm-withdraw"),
    path("applications/<int:pk>/cancel", v.CancelRequestView.as_view(), name="elm-cancel"),
    path("applications/<int:pk>/decide-cancellation", v.DecideCancelView.as_view(),
         name="elm-decide-cancellation"),
    path("applications/<int:pk>/recommend", v.RecommendView.as_view(), name="elm-recommend"),
    path("applications/<int:pk>/decide", v.DecideView.as_view(), name="elm-decide"),
    path("applications/<int:pk>/resume", v.SubmitResumptionView.as_view(), name="elm-resume"),
    path("applications/<int:pk>/review-resumption", v.ReviewResumptionView.as_view(),
         name="elm-review-resumption"),
    path("applications/<int:pk>/renominate-substitute", v.RenominateSubstituteView.as_view(),
         name="elm-renominate-substitute"),
    path("applications/<int:pk>/printable", v.PrintableView.as_view(), name="elm-printable"),
    path("substitute/<int:pk>/respond", v.SubstituteRespondView.as_view(),
         name="elm-substitute-respond"),
    path("substitute-inbox", v.SubstituteInboxView.as_view(), name="elm-substitute-inbox"),
    path("balances", v.BalancesView.as_view(), name="elm-balances"),
    path("inbox", v.InboxView.as_view(), name="elm-inbox"),
    path("offline", v.OfflineLeaveView.as_view(), name="elm-offline"),
    path("holidays", v.HolidaysView.as_view(), name="elm-holidays"),
    path("vacations", v.VacationCalendarView.as_view(), name="elm-vacations"),
]
