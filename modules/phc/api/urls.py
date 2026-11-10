from django.urls import path
from modules.phc.api.views import NotificationListView

urlpatterns = [
    path("notifications", NotificationListView.as_view(), name="notification-list"),
]
