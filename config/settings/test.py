from .base import *

DEBUG = False
IAM_BASE_URL = "http://iam.test"
IAM_SERVICE_TOKEN = "test-token"
IAM_SESSION_CACHE_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test"
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
