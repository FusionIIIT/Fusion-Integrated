"""SQLite-only isolated test database for environments without local PostgreSQL."""
from config.settings.test import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# The project migrations include PostgreSQL-specific operations. The A8 tests
# exercise BADMS services/models on this isolated SQLite test schema only.
MIGRATION_MODULES = {
    "directory": None,
    "accesscontrol": None,
    "placement": None,
    "badms": None,
}
