from .dev import *

DEBUG = False
# Tests never reach the real IAM — fusion_auth is stubbed via responses/monkeypatch.
IAM_BASE_URL = "http://iam.test"
IAM_SERVICE_TOKEN = "test-token"  # noqa: S105 — test fixture, never a real credential
IAM_SESSION_CACHE_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                      "LOCATION": "test"}}

# CI provides a real Postgres (see .github/workflows/ci.yml, which exports
# DB_PASSWORD). A lab machine may have no server at all, and a test suite
# you cannot run is not a test suite: with no credentials configured, fall
# back to SQLite. Nothing in the suite depends on server-side Postgres
# features (there is no contrib.postgres type anywhere in the codebase), and
# FUSION_TEST_ENGINE=postgresql forces the real database when one exists.
if env("FUSION_TEST_ENGINE", "postgresql") == "postgresql" and not env("DB_PASSWORD"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
            "OPTIONS": {"timeout": 20},
        }
    }
