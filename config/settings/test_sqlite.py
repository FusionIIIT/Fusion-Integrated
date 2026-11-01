from .base import *

DEBUG = False

# Use SQLite for tests - no PostgreSQL needed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test_db.sqlite3",
    }
}

# Tests never reach the real IAM — fusion_auth is stubbed via responses/monkeypatch.
IAM_BASE_URL = "http://iam.test"
IAM_SERVICE_TOKEN = "test-token"  # noqa: S105 — test fixture, never a real credential
IAM_SESSION_CACHE_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                      "LOCATION": "test"}}

# Use migrations
MIGRATION_MODULES = {}
