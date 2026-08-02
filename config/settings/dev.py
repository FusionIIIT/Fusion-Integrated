from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
CELERY_TASK_ALWAYS_EAGER = True

# Dev-only tooling: cross-cutting fixtures that legitimately touch every
# module. Never installed in production.
INSTALLED_APPS = [*INSTALLED_APPS, "devtools"]
