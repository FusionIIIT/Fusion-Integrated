from pathlib import Path

from .dev import *

DEBUG = False

# Isolate ELM tests from the development database and real IAM.
IAM_BASE_URL = "http://iam.test"
IAM_SERVICE_TOKEN = "test-token"
IAM_SESSION_CACHE_SECONDS = 0

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "elm-diagnostic",
    }
}

DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": str(Path(BASE_DIR) / "elm_diagnostic.sqlite3"),
}
MIGRATION_MODULES = {"placement": None}