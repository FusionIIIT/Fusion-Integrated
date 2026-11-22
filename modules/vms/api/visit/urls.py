from django.urls import path

from modules.vms.api.visit import views

urlpatterns = [
    path("visit/check-out", views.CheckOutView.as_view(), name="vms-visit-check-out"),
    path("visit/self-check-out", views.SelfCheckOutView.as_view(),
         name="vms-visit-self-check-out"),
    path("visit/passes/<int:pk>/terminate", views.TerminatePassView.as_view(),
         name="vms-visit-terminate"),
    path("visit/on-site", views.OnSiteView.as_view(), name="vms-visit-on-site"),
]
