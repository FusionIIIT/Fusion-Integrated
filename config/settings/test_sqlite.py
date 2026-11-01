"""Local SQLite tests; production/CI PostgreSQL settings are unchanged."""

from .test import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
# The unrelated placement migration history requires PostgreSQL-specific indexes.
# LMS migrations still run; placement is synchronized from its current models.
MIGRATION_MODULES = {"placement": None}
