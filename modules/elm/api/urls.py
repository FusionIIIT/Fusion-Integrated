from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("applications", v.LeaveListCreateView.as_view(), name="elm-applications"),
    path("applications/<int:pk>", v.LeaveDetailView.as_view(), name="elm-application"),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="elm-withdraw"),
    path("applications/<int:pk>/cancel", v.CancelView.as_view(), name="elm-cancel"),
    path("applications/<int:pk>/decide", v.DecideView.as_view(), name="elm-decide"),
    path("substitute/<int:pk>/respond", v.SubstituteRespondView.as_view(),
         name="elm-substitute-respond"),
    path("balances", v.BalancesView.as_view(), name="elm-balances"),
    path("inbox", v.InboxView.as_view(), name="elm-inbox"),
    path("holidays", v.HolidaysView.as_view(), name="elm-holidays"),
]
