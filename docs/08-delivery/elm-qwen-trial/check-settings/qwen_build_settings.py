from pathlib import Path
from config.settings.test import *
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(__file__).resolve().parent / "schema.sqlite3")}}
