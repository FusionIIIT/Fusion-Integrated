# config/settings/base.py
INSTALLED_APPS = (
    DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
    + PLATFORM_MODULES + DOMAIN_MODULES + ["modules.leave_elm"]
)
