from django.apps import AppConfig


class VmsConfig(AppConfig):
    name = "modules.vms"
    label = "vms"
    # Nothing here may import models at module scope. Any future wiring goes in
    # ready() with function-local imports.
