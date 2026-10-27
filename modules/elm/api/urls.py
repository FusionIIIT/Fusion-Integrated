from django.urls import path
from modules.elm.api import views as v

urlpatterns = [
    path("types", v.LeaveTypeListView.as_view(), name="elm-types"),
    path("requests", v.LeaveRequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>/transition", v.LeaveRequestTransitionView.as_view(), name="elm-request-transition"),
    path("balances", v.LeaveBalanceListView.as_view(), name="elm-balances"),
    path("substitute-responses", v.SubstituteResponseListView.as_view(), name="elm-substitute-responses"),
    path("substitute-responses/<int:pk>/respond", v.SubstituteResponseRespondView.as_view(), name="elm-substitute-respond"),
]
