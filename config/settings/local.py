from .dev import *

# Local development database.
# This does not modify the PostgreSQL configuration in base.py.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}