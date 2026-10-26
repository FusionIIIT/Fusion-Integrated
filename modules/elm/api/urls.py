from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("leave-requests/", views.LeaveRequestListView.as_view(), name="elm-leave-requests"),
    path("leave-requests/<int:pk>/", views.LeaveRequestDetailView.as_view(),
         name="elm-leave-request"),
    path("leave-requests/<int:pk>/withdraw/", views.LeaveRequestWithdrawView.as_view(),
         name="elm-leave-request-withdraw"),
    path("balance/", views.BalanceView.as_view(), name="elm-balance"),
]
