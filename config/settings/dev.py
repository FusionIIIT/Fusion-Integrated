from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
CELERY_TASK_ALWAYS_EAGER = True

# Dev-only fixtures that legitimately touch every module; never in production.
INSTALLED_APPS = [*INSTALLED_APPS, "devtools"]

# Local-only demo assignments for the two accounts shown in the DEPT setup.
# They do not create HOD/Dept_Admin appointments or affect non-dev settings.
DEPT_DEMO_USER_DEPARTMENTS = {5328: "CSE", 6565: "CSE"}
