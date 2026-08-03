import os

from .base import *

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]     # required, no fallback
DB_PASSWORD = os.environ["DB_PASSWORD"]          # required, no fallback
DATABASES["default"]["PASSWORD"] = DB_PASSWORD
IAM_SERVICE_TOKEN = os.environ["IAM_SERVICE_TOKEN"]
# Required, no fallback: a home-directory default is wrong on a server.
PLACEMENT_UPLOAD_ROOT = os.environ["PLACEMENT_UPLOAD_ROOT"]

# Required because their absence is silent and severe: LocMem makes every
# throttle per-worker, and memory:// means no task ever runs — so no
# notification is sent and no offer ever expires.
CACHES["default"] = {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": os.environ["REDIS_CACHE_URL"],
}
CELERY_BROKER_URL = os.environ["REDIS_BROKER_URL"]

# The base default is the console, which prints mail instead of sending it.
EMAIL_BACKEND = os.environ.get("DJANGO_EMAIL_BACKEND",
                               "django.core.mail.backends.smtp.EmailBackend")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# nginx terminates TLS; without this Django redirects forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
