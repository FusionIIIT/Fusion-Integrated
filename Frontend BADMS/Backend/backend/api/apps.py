from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        import os

        # Only start scheduler in the main process, not the reloader child
        if (
            os.environ.get("RUN_MAIN") != "true"
            and os.environ.get("RUN_MAIN") is not None
        ):
            return

        try:
            # Guard against running during migrate/makemigrations when tables
            # may not exist yet
            from django.db import connections

            existing = connections["default"].introspection.table_names()
            required = {"backup_schedules", "django_apscheduler_djangojob"}
            if not required.issubset(set(existing)):
                return

            from . import scheduler

            scheduler.start()
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Failed to start APScheduler")
