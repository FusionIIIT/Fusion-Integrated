"""SQLite test settings: lets the suite run with no database server.

Used only for local verification of the leave module. The committed CI
settings use Postgres; this file overrides DATABASES and nothing else.
"""
from .dev import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Keep the test suite repeatable regardless of the environment.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                      "LOCATION": "test-sqlite"}}
