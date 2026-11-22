from django.urls import path

from modules.vms.api.walkin import views

urlpatterns = [
    path("walkin/registrations", views.WalkinRegistrationsView.as_view(),
         name="vms-walkin-registrations"),
    path("walkin/registrations/<int:pk>/host-decision",
         views.WalkinHostDecisionView.as_view(), name="vms-walkin-host-decision"),
    path("walkin/registrations/<int:pk>/contingency",
         views.WalkinContingencyView.as_view(), name="vms-walkin-contingency"),
]
