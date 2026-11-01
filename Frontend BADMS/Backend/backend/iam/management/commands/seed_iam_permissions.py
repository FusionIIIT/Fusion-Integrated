"""Seed designation -> permission mappings from the platform's manifest.

    manage.py seed_iam_permissions --manifest .../registry/permissions.json

Idempotent, and authoritative only for the modules the manifest names: a grant
dropped upstream is revoked here, other modules are untouched.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from iam.models import (IamDesignationModule, IamModule, IamNavItem,
                        RolePermission)

#: 1 says nothing about navigation; 2 publishes it too.
SUPPORTED_VERSIONS = (1, 2)

#: Where the platform is deployed alongside this console.
DEFAULT_MANIFEST = Path("/srv/fusion/platform/current/registry/permissions.json")


class Command(BaseCommand):
    help = "Seed designation -> permission mappings from the platform manifest"

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest", type=Path, default=DEFAULT_MANIFEST,
            help=f"Path to registry/permissions.json (default {DEFAULT_MANIFEST})")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would change without writing.")
        parser.add_argument(
            "--publisher",
            help="Which service this manifest belongs to, when it does not "
                 "name itself. Its grants are scoped to this name.")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        manifest = self._load(opts["manifest"])
        publisher = manifest.get("publisher") or opts.get("publisher")
        if not publisher:
            raise CommandError(
                "This manifest does not name its publisher and --publisher was "
                "not given. Without it every service writes to the same rows "
                "and the last one to run revokes the others.")
        source = IamDesignationModule.manifest_source(publisher)
        self._refuse_foreign_modules(manifest, source)
        added, removed = self._apply(manifest, dry_run=dry_run, source=source,
                                     publisher=publisher)

        for line in removed:
            self.stdout.write(self.style.WARNING(
                f"  {'would revoke' if dry_run else 'revoked'} {line}"))
        self.stdout.write(self.style.SUCCESS(
            f"{len(added)} to add, {len(removed)} to revoke" if dry_run
            else f"{len(added)} added, {len(removed)} revoked; "
                 f"{RolePermission.objects.count()} total"))

    def _load(self, path: Path) -> dict:
        try:
            manifest = json.loads(path.read_text())
        except OSError as exc:
            raise CommandError(
                f"Cannot read {path}: {exc}. The platform writes it with "
                f"'make permissions'; pass --manifest if it lives elsewhere."
            ) from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"{path} is not valid JSON: {exc}") from exc

        version = manifest.get("version")
        if version not in SUPPORTED_VERSIONS:
            raise CommandError(
                f"{path} declares version {version!r}; this command "
                f"understands {SUPPORTED_VERSIONS}. Upgrade one side or the "
                f"other rather than guessing at the shape.")
        if not manifest.get("modules"):
            raise CommandError(f"{path} lists no modules — refusing to treat "
                               f"that as 'revoke everything'.")
        return manifest

    def _refuse_foreign_modules(self, manifest: dict, source: str) -> None:
        """A module another service already publishes is not ours to rewrite."""
        clashes = (IamDesignationModule.objects
                   .filter(module_code__in=manifest["modules"])
                   .filter(source__startswith=IamDesignationModule.MANIFEST_PREFIX)
                   .exclude(source=source)
                   .values_list("module_code", "source").distinct())
        if clashes:
            detail = ", ".join(f"{m} (owned by {s})" for m, s in sorted(clashes))
            raise CommandError(
                f"This manifest declares modules another service publishes: "
                f"{detail}. Seeding would revoke their grants. Rename the "
                f"module or agree one owner before re-running.")

    @transaction.atomic
    def _apply(self, manifest: dict, *, dry_run: bool, source: str,
               publisher: str):
        added, removed = [], []
        self._adopt_unattributed(manifest, source, dry_run=dry_run)
        self._apply_module_grants(manifest, dry_run=dry_run, added=added,
                                  removed=removed, source=source)
        self._apply_nav(manifest, dry_run=dry_run, source=source,
                        publisher=publisher)
        for module_code, spec in sorted(manifest["modules"].items()):
            wanted = {
                (designation, code)
                for designation, codes in spec.get("grants", {}).items()
                for code in codes
            }
            # Scoped to this module's prefix so another module's rows survive.
            existing = RolePermission.objects.filter(
                permission__startswith=f"{module_code}.")
            have = {(r.designation, r.permission) for r in existing}

            for designation, code in sorted(wanted - have):
                added.append(f"{designation}: {code}")
                if not dry_run:
                    RolePermission.objects.get_or_create(
                        designation=designation, permission=code)

            for designation, code in sorted(have - wanted):
                removed.append(f"{designation}: {code}")
                if not dry_run:
                    existing.filter(designation=designation,
                                    permission=code).delete()

            self.stdout.write(f"  {module_code}: {len(wanted)} mapping(s)")
        return added, removed

    def _adopt_unattributed(self, manifest, source, *, dry_run) -> None:
        """Rows seeded before publishers existed belong to whoever declares them now."""
        stale = IamDesignationModule.objects.filter(
            module_code__in=manifest["modules"],
            source=IamDesignationModule.MANIFEST)
        count = stale.count()
        if not count:
            return
        self.stdout.write(self.style.WARNING(
            f"  {'would adopt' if dry_run else 'adopted'} {count} unattributed "
            f"grant(s) as {source}"))
        if not dry_run:
            stale.update(source=source)

    def _apply_module_grants(self, manifest, *, dry_run, added, removed, source):
        """The coarse gate, alongside the fine one.

        Two separate checks guard every endpoint: may this role enter the module
        at all, and may it do this action. Seeding only the permissions leaves a
        user with every permission correct and every screen 403.

        Scoped to this publisher's own rows, so it never disturbs what the ERP
        projection grants, nor what another service publishes.
        """
        for module_code, spec in sorted(manifest["modules"].items()):
            if "module_grants" not in spec:
                # An older platform that predates this key states nothing about
                # the coarse gate. Reading silence as "revoke all" would lock
                # every user out of a module that is working fine.
                continue

            wanted = set(spec["module_grants"])
            # A dry run adopts nothing, so it must still read what adoption would claim.
            owned = ([source, IamDesignationModule.MANIFEST] if dry_run
                     else [source])
            existing = IamDesignationModule.objects.filter(
                module_code=module_code, source__in=owned)
            have = set(existing.values_list("designation", flat=True))

            for designation in sorted(wanted - have):
                added.append(f"{designation}: module {module_code}")
                if not dry_run:
                    IamDesignationModule.objects.get_or_create(
                        designation=designation, module_code=module_code,
                        source=source)

            for designation in sorted(have - wanted):
                removed.append(f"{designation}: module {module_code}")
                if not dry_run:
                    existing.filter(designation=designation).delete()

    def _apply_nav(self, manifest, *, dry_run, source, publisher) -> None:
        """The sidebar this service contributes, scoped to its own rows.

        A v1 manifest states nothing about navigation, so its modules keep
        whatever they already have: reading silence as "delete" would empty the
        sidebar of any service that has not published yet.
        """
        declared = {code: spec["nav"]
                    for code, spec in manifest["modules"].items()
                    if spec.get("nav")}
        if manifest.get("version", 1) < 2:
            return

        for code, nav in sorted(declared.items()):
            if dry_run:
                self.stdout.write(f"  {code}: {len(nav['items'])} nav item(s)")
                continue
            module, _ = IamModule.objects.update_or_create(
                code=code, source=source,
                defaults={"app": publisher,
                          **{k: v for k, v in nav.items() if k != "items"}})
            for item in nav["items"]:
                IamNavItem.objects.update_or_create(
                    code=item["code"], source=source,
                    defaults={**{k: v for k, v in item.items() if k != "code"},
                              "module": module})
            wanted = [i["code"] for i in nav["items"]]
            module.nav_items.exclude(code__in=wanted).delete()

        if dry_run:
            return
        # A module this service used to publish and no longer does.
        stale = IamModule.objects.filter(source=source).exclude(code__in=declared)
        for code in stale.values_list("code", flat=True):
            self.stdout.write(self.style.WARNING(
                f"  {code}: no longer published by {publisher} — nav removed"))
        stale.delete()
