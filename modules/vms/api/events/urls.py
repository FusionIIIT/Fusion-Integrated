from django.urls import path

from modules.vms.api.events import views as v

urlpatterns = [
    path("events", v.EventListView.as_view(), name="vms-events"),
    path("events/<int:pk>", v.EventDetailView.as_view(), name="vms-event"),
    path("events/<int:pk>/attendees", v.AttendeeListView.as_view(), name="vms-event-attendees"),
    path("events/<int:pk>/attendees/upload", v.AttendeeUploadView.as_view(),
         name="vms-event-upload"),
    path("events/<int:pk>/attendees/<int:aid>", v.AttendeeDetailView.as_view(),
         name="vms-event-attendee"),
    path("events/<int:pk>/approve", v.ApproveView.as_view(), name="vms-event-approve"),
    path("events/<int:pk>/cancel", v.CancelView.as_view(), name="vms-event-cancel"),
    path("events/<int:pk>/attendance", v.AttendanceView.as_view(), name="vms-event-attendance"),
    path("events/<int:pk>/throughput", v.ThroughputView.as_view(), name="vms-event-throughput"),
    path("events/<int:pk>/fast-lane-manifest", v.FastLaneManifestView.as_view(),
         name="vms-event-manifest"),
]
