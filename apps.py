from django.apps import AppConfig
from django.core.checks import register


class ELMConfig(AppConfig):
    name = "modules.elm"
    label = "elm"
    verbose_name = "Example Module"

    def ready(self) -> None:
        # ELM_UPLOAD_ROOT is this module's setting, so it owns the check.
        from core.files.checks import check_upload_root

        register(check_upload_root)
```

registry.py
