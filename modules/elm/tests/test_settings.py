"""Test settings for ELM module test suite.

Inherits full platform test configuration and configures in-memory SQLite for local test execution.
Bypasses PostgreSQL-specific migration operations during in-memory SQLite setup.
"""
from config.settings.test import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()
