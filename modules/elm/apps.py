from django.apps import AppConfig
from django.core.checks import register


class ElmConfig(AppConfig):
    name = "modules.elm"
    label = "elm"
