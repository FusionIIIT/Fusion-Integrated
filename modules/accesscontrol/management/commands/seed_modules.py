"""Register the modules and their menus.

Idempotent — safe to re-run on every deploy. Each module declares its own
registry rows in modules/<name>/registry.py, so adding a module never means
editing a central list.
"""
from importlib import import_module

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from modules.accesscontrol.models import Module, NavItem


class Command(BaseCommand):
    help = "Seed the module registry from each module's registry.py"

    @transaction.atomic
    def handle(self, *args, **options):
        seeded = 0
        for cfg in apps.get_app_configs():
            if not cfg.name.startswith("modules."):
                continue
            try:
                reg = import_module(f"{cfg.name}.registry")
            except ModuleNotFoundError:
                continue
            spec = getattr(reg, "MODULE", None)
            if not spec:
                continue

            # A module may declare what it needs before it can work.
            unmet = list(getattr(reg, "readiness", list)() or [])
            defaults = {k: v for k, v in spec.items() if k != "code"}
            if unmet:
                defaults["status"] = "planned"

            module, _ = Module.objects.update_or_create(
                code=spec["code"], defaults=defaults
            )
            if unmet:
                self.stdout.write(self.style.WARNING(
                    f"  {spec['code']}: registered but NOT active — "
                    f"{len(unmet)} prerequisite(s) unmet:"))
                for reason in unmet:
                    self.stdout.write(self.style.WARNING(f"      {reason}"))
            for item in getattr(reg, "NAV_ITEMS", []):
                NavItem.objects.update_or_create(
                    code=item["code"],
                    defaults={**{k: v for k, v in item.items() if k != "code"},
                              "module": module},
                )
            seeded += 1
            self.stdout.write(f"  registered {spec['code']} ({spec['status']})")
        self.stdout.write(self.style.SUCCESS(f"{seeded} module(s) registered"))
