"""IWD module registry entry."""
from registry.types import ModuleMeta

MODULE = ModuleMeta(
    name="iwd",
    verbose_name="Institute Work Department",
    installed_app="modules.iwd",
    app_label="iwd",
    api_url_prefix="iwd",
    api_urls="modules.iwd.api.urls",
    contract_module="modules.iwd.contracts",
    is_platform=False,
)

