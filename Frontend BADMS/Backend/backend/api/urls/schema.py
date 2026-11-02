from django.urls import path

from ..views import schema

urlpatterns = [
    path("update-globals-db/", schema.update_globals_db, name="update_globals_db"),
]
