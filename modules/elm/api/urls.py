from django.urls import path

from modules.elm.api.views import LeaveApplicationListCreateView

urlpatterns = [
    path("leave-applications", LeaveApplicationListCreateView.as_view(),
         name="elm-leave-applications"),
]