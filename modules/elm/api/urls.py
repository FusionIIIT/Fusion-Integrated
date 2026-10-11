from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("balances", views.BalanceView.as_view(), name="elm-balances"),
    path("requests", views.RequestListCreateView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", views.RequestDetailView.as_view(), name="elm-request"),
    path("admin/<str:resource>", views.AdminDataView.as_view(), name="elm-admin-resource"),
    path(
        "admin/<str:resource>/<int:pk>",
        views.AdminDataView.as_view(),
        name="elm-admin-resource-detail",
    ),
    path(
        "admin/calendars/<int:pk>/publish",
        views.CalendarPublishView.as_view(),
        name="elm-calendar-publish",
    ),
]
