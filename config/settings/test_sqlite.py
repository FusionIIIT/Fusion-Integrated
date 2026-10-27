"""Opt-in local test settings when PostgreSQL is unavailable.

Run: python -m pytest --ds=config.settings.test_sqlite modules/elm/tests
CI continues to use PostgreSQL via config.settings.test. SQLite tests do not
verify PostgreSQL row-lock or concurrent transaction behavior.
"""

from .test import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
# Placement's historical PostgreSQL index migration cannot run on SQLite.
# Only that unrelated app is synchronized from its current models. ELM's real
# migrations still run. This setting must not be used to certify placement.
MIGRATION_MODULES = {"placement": None}
