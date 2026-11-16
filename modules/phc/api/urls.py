from django.urls import path

from modules.phc.api import views as v

urlpatterns = [
    path("schedules", v.ScheduleListCreateView.as_view(), name="phc-schedules"),
    path(
        "schedules/<int:pk>",
        v.ScheduleDetailView.as_view(),
        name="phc-schedule",
    ),
    path(
        "schedules/<int:pk>/publish",
        v.SchedulePublishView.as_view(),
        name="phc-schedule-publish",
    ),
    path(
        "schedules/<int:pk>/presence",
        v.SchedulePresenceView.as_view(),
        name="phc-schedule-presence",
    ),
    path("records/mine", v.MyVisitListView.as_view(), name="phc-records-mine"),
    path("visits", v.VisitListCreateView.as_view(), name="phc-visits"),
]
