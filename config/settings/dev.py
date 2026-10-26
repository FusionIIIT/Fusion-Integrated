from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
CELERY_TASK_ALWAYS_EAGER = True

# Dev-only fixtures that legitimately touch every module; never in production.
INSTALLED_APPS = [*INSTALLED_APPS, "devtools"]

# In local dev without running Fusion_System_Administrator on port 8001,
# mock IAM allows seamless login as any user/admin.
DEV_MOCK_IAM = env_bool("DEV_MOCK_IAM", True)
