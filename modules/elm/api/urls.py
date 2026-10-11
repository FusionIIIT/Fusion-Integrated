from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("applications", views.ApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/approve", views.ApproveView.as_view(),
         name="elm-approve"),
    path("balances", views.BalancesView.as_view(), name="elm-balances"),
]
