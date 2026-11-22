import os
from .dev import *  # noqa: F403

DEBUG = False
# Tests never reach the real IAM — fusion_auth is stubbed via responses/monkeypatch.
IAM_BASE_URL = "http://iam.test"
IAM_SERVICE_TOKEN = "test-token"  # noqa: S105 — test fixture, never a real credential
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
IAM_SESSION_CACHE_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                      "LOCATION": "test"}}

# In local developer environments without Postgres running, fall back to SQLite for tests.
# In CI (where DB_HOST is set) or when configured, PostgreSQL is used.
if not os.environ.get("DB_HOST") and not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    MIGRATION_MODULES = {
        "placement": None,
    }
