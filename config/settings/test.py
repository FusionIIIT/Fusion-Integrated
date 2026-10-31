from .dev import *

DEBUG = False
# Tests never reach the real IAM — fusion_auth is stubbed via responses/monkeypatch.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "elm_test.sqlite3",
    }
}

MIGRATION_MODULES = {
    "placement": None,
}