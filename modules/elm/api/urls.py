from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("leave-requests", v.LeaveRequestListView.as_view(), name="elm-leave-requests"),
    path("leave-requests/<int:pk>", v.LeaveRequestDetailView.as_view(),
         name="elm-leave-request"),
    path("leave-types", v.LeaveTypeListView.as_view(), name="elm-leave-types"),
    path("leave-types/<int:pk>", v.LeaveTypeDetailView.as_view(),
         name="elm-leave-type"),
    path("leave-balances", v.LeaveBalanceListView.as_view(), name="elm-leave-balances"),
    path("leave-balances/<int:pk>", v.LeaveBalanceDetailView.as_view(),
         name="elm-leave-balance"),
]
