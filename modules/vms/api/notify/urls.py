from django.urls import path

from modules.vms.api.notify import views

urlpatterns = [
    path("notify/inbox", views.InboxView.as_view(), name="vms-notify-inbox"),
    path("notify/unread-count", views.UnreadCountView.as_view(), name="vms-notify-unread"),
    path("notify/read-all", views.ReadAllView.as_view(), name="vms-notify-read-all"),
    path("notify/arrivals", views.ArrivalsView.as_view(), name="vms-notify-arrivals"),
    path("notify/outbox", views.OutboxView.as_view(), name="vms-notify-outbox"),
    path("notify/outbox/<int:pk>/retry", views.OutboxRetryView.as_view(),
         name="vms-notify-outbox-retry"),
    path("notify/<int:pk>/read", views.MarkReadView.as_view(), name="vms-notify-read"),
    path("visitor/notifications", views.VisitorInboxView.as_view(),
         name="vms-visitor-notifications"),
    path("visitor/notifications/<int:pk>/read", views.VisitorMarkReadView.as_view(),
         name="vms-visitor-notification-read"),
]
