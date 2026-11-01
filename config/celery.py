import os

from celery import Celery

from modules.placement.schedule import (
    BEAT_SCHEDULE as PLACEMENT_SCHEDULE,
)
from modules.placement.schedule import (
    TASK_ROUTES as PLACEMENT_ROUTES,
)
from modules.complaint_cms.schedule import (
    BEAT_SCHEDULE as CMS_SCHEDULE,
    TASK_ROUTES as CMS_ROUTES,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
app = Celery("fusion_integrated")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Each module owns its timers; this only merges them, so modules stay removable.
app.conf.beat_schedule = {**PLACEMENT_SCHEDULE, **CMS_SCHEDULE}
app.conf.task_routes = {**PLACEMENT_ROUTES, **CMS_ROUTES}
