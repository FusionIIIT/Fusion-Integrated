"""Publish the permission catalogue and its designation grants for the IAM to seed.

    manage.py permission_manifest            write registry/permissions.json
    manage.py permission_manifest --check    fail if stale or ungrantable
"""
import json
import re
from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

MANIFEST = Path(settings.BASE_DIR) / "registry" / "permissions.json"
CATALOGUE = (Path(settings.BASE_DIR) / "docs" / "02-iam"
             / "permission-catalog.generated.md")
VERSION = 1


def collect() -> dict:
    modules = {}
    for cfg in sorted(apps.get_app_configs(), key=lambda c: c.name):
        if not cfg.name.startswith("modules."):
            continue
        try:
            reg = import_module(f"{cfg.name}.registry")
        except ModuleNotFoundError:
            continue
        if not getattr(reg, "PERMISSIONS", None):
            continue
        spec = getattr(reg, "MODULE", None)
        # A module with permissions but no screens still owns its grants.
        code = spec["code"] if spec else cfg.label
        modules[code] = {
            "permissions": [
                {"code": code, "label": label}
                for code, label in getattr(reg, "PERMISSIONS", [])
            ],
            "system_permissions": sorted(getattr(reg, "SYSTEM_PERMISSIONS", [])),
            # Enforced by narrowing a queryset rather than by refusing a
            # request. Holding one widens what you see; not holding it shows
            # you less. There is no endpoint to check it in, so the
            # unenforced check has to be told.
            "scope_permissions": sorted(getattr(reg, "SCOPE_PERMISSIONS", [])),
            "grants": {
                designation: sorted(set(codes))
                for designation, codes
                in sorted(getattr(reg, "ROLE_GRANTS", {}).items())
            },
            # Derived, never listed separately. A designation holding any of a
            # module's permissions must be able to enter the module — the two
            # gates are separate checks, and seeding only one leaves every screen
            # 403 with the permissions apparently correct.
            "module_grants": sorted(
                designation
                for designation, codes in getattr(reg, "ROLE_GRANTS", {}).items()
                if codes),
        }
    return {"version": VERSION, "modules": modules}


def problems(manifest: dict) -> list[str]:
    found = []
    for code, spec in manifest["modules"].items():
        declared = {p["code"] for p in spec["permissions"]}
        system = set(spec["system_permissions"])
        scoped = set(spec.get("scope_permissions", []))
        granted = {c for codes in spec["grants"].values() for c in codes}

        found.extend(
            f"{code}: {orphan} is declared but no designation holds it, so the "
            f"endpoint guarding on it is unreachable. Grant it in ROLE_GRANTS, "
            f"or list it in SYSTEM_PERMISSIONS if only a service performs it."
            for orphan in sorted(declared - system - granted))
        found.extend(
            f"{code}: {unknown} is granted but not in PERMISSIONS — a typo "
            f"there grants nothing at all."
            for unknown in sorted(granted - declared))
        found.extend(
            f"{code}: {wrong} does not carry the module's prefix, so the IAM "
            f"cannot tell which module owns it."
            for wrong in sorted(c for c in declared
                                if not c.startswith(f"{code}.")))
        found.extend(
            f"{code}: {both} is both a system permission and granted to a "
            f"designation. Pick one."
            for both in sorted(system & granted))
        # None means the module's code could not be located, so there is
        # nothing to judge. Reporting every permission as unenforced in that
        # case is exactly the failure this check is meant to prevent.
        # A system permission is enforced by whichever service calls it, which
        # need not be inside this module, so it is out of scope here.
        enforced = _enforced(code)
        if enforced is not None:
            found.extend(
                f"{code}: {unused} is declared and granted, but no endpoint or "
                f"service checks it — so the thing it names cannot be done at "
                f"all. Either the feature is missing, or the permission is."
                for unused in sorted(
                    declared - system - scoped - enforced - KNOWN_UNENFORCED))
    return found


def known_gaps(manifest: dict) -> list[str]:
    """The allowlisted ones that are still true, so they stay countable.

    Reported on every run rather than suppressed. An allowlist nobody sees is
    how a temporary exception becomes permanent.
    """
    return sorted(
        code for spec_code, spec in manifest["modules"].items()
        for code in ({p["code"] for p in spec["permissions"]}
                     & KNOWN_UNENFORCED) - (_enforced(spec_code) or set()))





#: Permissions declared before the check existed, whose feature has not
#: been built yet. Each is a real gap, listed so a NEW one fails CI
#: immediately instead of joining a pile nobody counts. Deleting a line
#: here is the definition of done for that feature.
KNOWN_UNENFORCED = frozenset({
})


def _module_paths() -> dict[str, Path]:
    """Module code -> the directory its code lives in.

    Resolved through the app registry, not by joining the code onto a path: the
    placement module's code is `placement_cell` while its package is
    `modules.placement`, and guessing the directory found nothing and reported
    every one of its 21 permissions as unenforced.
    """
    out: dict[str, Path] = {}
    for cfg in apps.get_app_configs():
        if not cfg.name.startswith("modules."):
            continue
        try:
            reg = import_module(f"{cfg.name}.registry")
        except ModuleNotFoundError:
            continue
        spec = getattr(reg, "MODULE", None)
        out[spec["code"] if spec else cfg.label] = Path(cfg.path)
    return out


def _enforced(module_code: str) -> set[str] | None:
    """Permission codes that appear anywhere in the module's own code.

    A grep, deliberately: a permission is enforced by being passed to
    HasPermission or authz.require, and both take a plain string. Anything
    cleverer would be a static analysis that the next way of checking defeats.

    `selectors/` does not count. That is the architecture's own line: a
    selector decides what you can see and authorises nothing, so a permission
    appearing only there hid three `*.manage` permissions whose write path did
    not exist.

    `domain/` does count. It holds the tables that say which permission a step
    needs — STEP_PERMISSIONS, OFFICE_PERMISSIONS — and the service reads them
    to make the check. That is authority stated once rather than inlined.

    registry.py is skipped because that is where they are declared, and tests
    because a test naming a permission is not an endpoint enforcing it.
    """
    root = _module_paths().get(module_code)
    if root is None:
        return None
    found: set[str] = set()
    for path in root.rglob("*.py"):
        parts = set(path.parts)
        if "tests" in parts or path.name == "registry.py":
            continue
        if "selectors" in parts:
            continue
        found.update(re.findall(rf"{re.escape(module_code)}\.[a-z_]+\.[a-z_]+",
                                path.read_text()))
    return found


def render(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def render_catalogue(manifest: dict) -> str:
    lines = [
        "# Permission catalogue (generated)",
        "",
        "Generated by `make permissions` from each module's `registry.py`, and",
        "checked in CI. Every code below is one a view or service actually",
        "guards on, and every designation column is one the IAM can grant.",
        "",
        "For the intended taxonomy of modules not yet built, see",
        "[permission-catalog.md](permission-catalog.md).",
    ]
    for code, spec in sorted(manifest["modules"].items()):
        system = set(spec["system_permissions"])
        holders = {
            p["code"]: sorted(d for d, codes in spec["grants"].items()
                              if p["code"] in codes)
            for p in spec["permissions"]
        }
        lines += ["", f"## `{code}`", "",
                  "| Code | What it allows | Held by |", "|---|---|---|"]
        for p in spec["permissions"]:
            who = ("_service only_" if p["code"] in system
                   else ", ".join(f"`{d}`" for d in holders[p["code"]]))
            lines.append(f"| `{p['code']}` | {p['label']} | {who} |")
    return "\n".join(lines) + "\n"


class Command(BaseCommand):
    help = "Write or verify registry/permissions.json"

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true",
                            help="Verify without writing.")

    def handle(self, *args, **opts):
        manifest = collect()
        found = problems(manifest)
        if found:
            raise CommandError("\n".join(["permission manifest is invalid:",
                                          *(f"  - {p}" for p in found)]))

        artifacts = {MANIFEST: render(manifest),
                     CATALOGUE: render_catalogue(manifest)}
        if opts["check"]:
            for path, body in artifacts.items():
                current = path.read_text() if path.exists() else ""
                if current != body:
                    raise CommandError(
                        f"{path.relative_to(settings.BASE_DIR)} is stale — run "
                        f"'make permissions'")
            self.stdout.write("permission manifest matches the registries")
            return

        for path, body in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        counts = ", ".join(
            f"{code}: {len(spec['permissions'])} permission(s), "
            f"{len(spec['grants'])} designation(s)"
            for code, spec in manifest["modules"].items())
        self.stdout.write(self.style.SUCCESS(
            f"wrote {MANIFEST.relative_to(settings.BASE_DIR)} — {counts}"))
