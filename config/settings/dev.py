from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
CELERY_TASK_ALWAYS_EAGER = True

# Dev-only fixtures that legitimately touch every module; never in production.
INSTALLED_APPS = [*INSTALLED_APPS, "devtools"]
