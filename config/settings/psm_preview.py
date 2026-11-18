import os
from .dev import *

PSM_PREVIEW = True
DEBUG = False
SECRET_KEY = os.environ["PSM_PREVIEW_SECRET"]
PSM_PREVIEW_KEY = os.environ["PSM_PREVIEW_KEY"]
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".trycloudflare.com", ".ngrok-free.dev"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "var/psm-preview.sqlite3"}}
ROOT_URLCONF = "devtools.psm_preview_urls"
REST_FRAMEWORK = {**REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": ["devtools.psm_preview_auth.PreviewAuthentication"]}

# Isolated PSM database: placement migrations require the production PostgreSQL schema.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "modules.placement"]
DOMAIN_MODULES = ["modules.psm"]
PSM_UPLOAD_ROOT = BASE_DIR / "var/psm-uploads"
