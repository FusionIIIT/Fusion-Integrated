from django.urls import path

from modules.elm.api import views as v


urlpatterns = [
    path("requests", v.MyLeaveRequestsView.as_view(), name="elm-my-requests"),
    path("requests/submit", v.LeaveRequestSubmitView.as_view(),
         name="elm-request-submit"),
]
