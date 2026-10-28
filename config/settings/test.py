from .dev import *

DEBUG = False
# Tests use an isolated database and do not require a running PostgreSQL service.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
# The placement app has a PostgreSQL-specific historical migration sequence.
MIGRATION_MODULES = {"placement": None}
# Tests never reach the real IAM — fusion_auth is stubbed via responses/monkeypatch.
IAM_BASE_URL = "http://iam.test"
IAM_SERVICE_TOKEN = "test-token"  # noqa: S105 — test fixture, never a real credential
IAM_SESSION_CACHE_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                      "LOCATION": "test"}}
