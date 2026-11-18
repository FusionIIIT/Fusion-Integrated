from .test import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Isolated PSM database: placement migrations require the production PostgreSQL schema.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "modules.placement"]
DOMAIN_MODULES = ["modules.psm"]
ROOT_URLCONF = "modules.psm.tests.urls"
