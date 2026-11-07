from django.apps import AppConfig
from django.core.checks import register


class PatentConfig(AppConfig):
    name = "modules.patent"
    label = "patent"

    def ready(self):
        # PMS does not own a global upload root check; it relies on the platform's
        # configuration (e.g., PLACEMENT_UPLOAD_ROOT or similar) for file storage.
        # No custom checks registered here to avoid duplication with placement.
        pass
