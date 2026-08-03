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
