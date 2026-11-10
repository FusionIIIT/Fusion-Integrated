from django.urls import path

from modules.iaa.api import views as v

urlpatterns = [
    path("session", v.SessionView.as_view()),
    path("requests", v.RequestsView.as_view()),
    path("requests/<int:pk>", v.RequestDetailView.as_view()),
    path("requests/<int:pk>/<str:action>", v.ActionView.as_view()),
    path("anomalies", v.AnomaliesView.as_view()),
    path("anomalies/<int:pk>/resolve", v.ResolveView.as_view()),
    path("observations", v.ObservationsView.as_view()),
    path("observations/<int:pk>/<str:action>", v.ObservationActionView.as_view()),
    path("notifications", v.NotificationsView.as_view()),
    path("reports", v.ReportsView.as_view()),
    path("config/<str:resource>", v.ConfigView.as_view()),
    path("recovery/<int:pk>", v.RecoverView.as_view()),
]
