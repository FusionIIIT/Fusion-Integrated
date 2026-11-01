from django.urls import path

from modules.department.api import views as v


urlpatterns = [
    path(
        "announcements/drafts",
        v.AnnouncementDraftCreateView.as_view(),
        name="department-announcement-draft",
    ),
    path(
        "announcements/<int:pk>/publish",
        v.AnnouncementPublishView.as_view(),
        name="department-announcement-publish",
    ),
    path(
        "announcements/<int:pk>/hide",
        v.AnnouncementHideView.as_view(),
        name="department-announcement-hide",
    ),
    path(
        "announcements/<int:pk>",
        v.AnnouncementDeleteView.as_view(),
        name="department-announcement-delete",
    ),
]
