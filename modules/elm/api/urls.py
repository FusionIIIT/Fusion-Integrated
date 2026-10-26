from django.urls import path

from .views import LeaveApplicationListCreateView, LeaveTypeListView

urlpatterns = [
    path("leave-types", LeaveTypeListView.as_view(), name="elm-leave-types"),
    path("applications", LeaveApplicationListCreateView.as_view(),
         name="elm-leave-applications"),
]
