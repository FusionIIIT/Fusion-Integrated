"""The module mounted where config/urls.py mounts it, for API tests."""
from django.urls import include, path

from config.urls import urlpatterns as platform

urlpatterns = [
    *platform,
    path("api/v1/visitorhostel/", include("modules.visitor_hostel.api.urls")),
]
