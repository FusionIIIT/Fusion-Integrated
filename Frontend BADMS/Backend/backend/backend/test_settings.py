from .settings import *

# Pinned, not inherited: settings.py reads this from the environment, so a
# developer with a real or malformed key exported would run a different suite.
# Empty means _get_fernet() returns None and encryption is skipped.
BACKUP_ENCRYPTION_KEY = ""

# Same reason: settings.py turns this on whenever DEBUG is off, so a shell
# without DEBUG=True exported made every request 301 to https and the whole
# suite fail on status codes.
SECURE_SSL_REDIRECT = False

# Two aliases, because SystemDBRouter routes by alias and its allow_migrate()
# builds each app's tables on exactly one of them. With `default` alone, every
# app in route_app_labels (auth, sessions, contenttypes, authtoken, iam) was
# built nowhere at all — which is why authenticated requests came back 401 in
# tests: the auth tables did not exist.
#
# Separate in-memory SQLite databases, mirroring the real separation:
#   default    the ERP — only managed=False shadows, so no tables are created
#   system_db  this tool's own data, including IAM
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        # Dummy values to satisfy _get_db_config keys
        "USER": "user",
        "PASSWORD": "password",
        "HOST": "localhost",
        "PORT": "5432",
    },
    "system_db": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "user",
        "PASSWORD": "password",
        "HOST": "localhost",
        "PORT": "5432",
    },
}

# Same reason again: whether a role policy violation is refused or merely
# reported is a deployment decision, and a suite whose result depends on the
# local .env is not a suite. Tests that care set it with override_settings.
IAM_ENFORCE_ROLE_POLICY = False
