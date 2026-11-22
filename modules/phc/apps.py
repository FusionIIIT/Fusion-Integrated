"""PHC - Primary Health Centre module."""

from django.apps import AppConfig


class PhcConfig(AppConfig):
    name = "modules.phc"
    label = "phc"

    def ready(self) -> None:
        # Import signal handlers so the notification outbox is populated.
        import modules.phc.services.notifications  # noqa: F401
