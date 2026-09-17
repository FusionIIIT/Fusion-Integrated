"""The guard that makes an unreachable endpoint a CI failure rather than a 403."""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.accesscontrol.management.commands.permission_manifest import problems


def _manifest(permissions, grants, system=()):
    return {"version": 1, "modules": {"m": {
        "permissions": [{"code": c, "label": c} for c in permissions],
        "system_permissions": sorted(system),
        "grants": grants,
    }}}


def test_a_permission_nobody_holds_is_reported():
    found = problems(_manifest(["m.thing.do"], {}))
    assert len(found) == 1
    assert "unreachable" in found[0]


def test_a_system_permission_may_have_no_holder():
    assert problems(_manifest(["m.thing.do"], {}, system=["m.thing.do"])) == []


def test_a_granted_code_that_is_not_declared_is_reported():
    found = problems(_manifest([], {"role": ["m.typo.here"]}))
    assert any("not in PERMISSIONS" in p for p in found)


def test_a_code_without_the_module_prefix_is_reported():
    found = problems(_manifest(["other.thing.do"], {"role": ["other.thing.do"]}))
    assert any("prefix" in p for p in found)


def test_a_code_cannot_be_both_system_and_granted():
    found = problems(_manifest(["m.thing.do"], {"role": ["m.thing.do"]},
                               system=["m.thing.do"]))
    assert any("Pick one" in p for p in found)


def test_the_committed_manifest_matches_the_registries():
    """Same assertion `make check` makes, so a stale file fails here too."""
    try:
        call_command("permission_manifest", check=True)
    except CommandError as exc:                            # pragma: no cover
        pytest.fail(str(exc))


def test_system_permissions_must_be_bare_codes():
    """The check that keeps the manifest honest was itself shape-blind."""
    from modules.accesscontrol.management.commands.permission_manifest import _codes

    with pytest.raises(CommandError, match="permission code strings"):
        _codes("modules.example", "SYSTEM_PERMISSIONS",
               [("m.thing.do", "Do the thing")])


def test_bare_codes_are_accepted():
    from modules.accesscontrol.management.commands.permission_manifest import _codes

    assert _codes("modules.example", "SYSTEM_PERMISSIONS", ["m.thing.do"]) == [
        "m.thing.do"]


def test_every_module_declares_system_permissions_the_same_way():
    """Read from the real registries, so a new module cannot drift."""
    from importlib import import_module

    from django.apps import apps

    for cfg in apps.get_app_configs():
        if not cfg.name.startswith("modules."):
            continue
        try:
            reg = import_module(f"{cfg.name}.registry")
        except ModuleNotFoundError:
            continue
        declared = getattr(reg, "SYSTEM_PERMISSIONS", [])
        assert all(isinstance(d, str) for d in declared), cfg.name
