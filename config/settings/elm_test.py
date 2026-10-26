"""Portable ELM verification only. Production keeps the PostgreSQL settings."""
from .test import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Placement migrations include PostgreSQL-specific index operations.
# ELM migrations still run; unrelated Placement tables use their current model schema.
MIGRATION_MODULES = {"placement": None}
