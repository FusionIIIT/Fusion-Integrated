"""One fact, one owner — enforced, not remembered.

The ERP owns people and the posts they hold; the IAM owns who may do what; this
service owns its own business data and asks the IAM for the rest over HTTP. The
two ways that breaks are a second database alias pointed at the ERP, and a local
table that re-implements a table the IAM already has. Both are cheap to check
and expensive to discover later.
"""
import importlib.util
import pkgutil
from pathlib import Path

from django.apps import apps
from django.conf import settings

#: Anything matching these is access control, and access control lives in the IAM.
RBAC_MODEL_NAMES = {"role", "permission", "userrole", "rolepermission",
                    "moduleaccess", "usergroup", "acl", "grant"}


def test_this_service_has_exactly_one_database():
    """A second alias is how a module ends up querying — then writing — the ERP."""
    assert list(settings.DATABASES) == ["default"]


def test_that_database_is_not_the_erp():
    assert settings.DATABASES["default"]["NAME"] != "fusionlab"


def test_no_module_declares_its_own_access_control_table():
    offenders = [
        f"{m._meta.app_label}.{m.__name__}"
        for m in apps.get_models()
        if m._meta.app_label.startswith("modules")
        and m.__name__.lower() in RBAC_MODEL_NAMES
    ]
    assert not offenders, (
        f"{offenders} duplicate tables the IAM already owns. Declare the "
        f"permission in the module's registry.py instead.")


def test_nothing_imports_the_erp_directly():
    """The IAM's client is the only way in. An import of a legacy app here
    means somebody wired a second path to the same rows."""
    import modules

    banned = ("applications.", "FusionIIIT", "globals.models")
    offenders = []
    for mod in pkgutil.walk_packages(modules.__path__, "modules."):
        if ".tests" in mod.name or ".migrations" in mod.name:
            continue
        spec = importlib.util.find_spec(mod.name)
        if spec is None or not spec.origin or not spec.origin.endswith(".py"):
            continue
        source = Path(spec.origin).read_text()
        if any(f"import {b}" in source for b in banned):
            offenders.append(mod.name)
    assert not offenders, f"{offenders} import the ERP directly"
