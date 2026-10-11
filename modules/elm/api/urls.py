from django.urls import path

from modules.elm.api.views import MyLeaveActionView, MyLeaveRequestsView

urlpatterns = [
    path("requests", MyLeaveRequestsView.as_view(), name="elm-requests"),
    path(
        "requests/<int:pk>/<str:action>",
        MyLeaveActionView.as_view(),
        name="elm-request-action",
    ),
]
