from django.urls import path

from modules.department.api.announcements import AnnouncementListView

urlpatterns = [
    path("announcements", AnnouncementListView.as_view(), name="department-announcements"),
]
