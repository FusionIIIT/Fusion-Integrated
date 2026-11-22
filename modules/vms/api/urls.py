from django.urls import include, path

# One url module per area; each lane fills in its own and never edits this file.
_AREAS = (
    "visitor", "host", "gate", "zones", "admin", "walkin", "visit",
    "notify", "monitor", "muster", "events", "reports", "extensions",
)

urlpatterns = [
    path("", include(f"modules.vms.api.{area}.urls")) for area in _AREAS
]
