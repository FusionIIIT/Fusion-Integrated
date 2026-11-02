from django.urls import path

from ..views import archive

urlpatterns = [
    path("archive/list/", archive.list_people, name="archive-list"),
    path("archive/action/", archive.archive_people, name="archive-action"),
    path("archive/restore/", archive.restore_people, name="archive-restore"),
]
