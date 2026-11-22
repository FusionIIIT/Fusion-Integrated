from .base import *  # noqa: F403

SECRET_KEY = "test-only-secret-key-not-for-production"
DEBUG = False

IAM_SESSION_CACHE_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test",
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
MIGRATION_MODULES = {"placement": None}
