from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
CELERY_TASK_ALWAYS_EAGER = True

# Dev-only fixtures that legitimately touch every module; never in production.
INSTALLED_APPS = [*INSTALLED_APPS, "devtools"]

# No ClamAV on a laptop or in CI; this backend refuses to run unless DEBUG is on.
PMS_MALWARE_SCANNER = env("PMS_MALWARE_SCANNER", "development")
