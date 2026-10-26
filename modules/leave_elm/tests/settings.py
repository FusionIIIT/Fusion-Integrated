SECRET_KEY = "elm-tests-only"
DEBUG = False
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "modules.leave_elm.api.urls"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "rest_framework",
    "modules.leave_elm",
]
ROOT_URLCONF = "modules.leave_elm.api.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None}
