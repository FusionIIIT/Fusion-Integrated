#!/usr/bin/env python
"""No ForeignKey may cross a module boundary.

Once an FK exists you get a join, cascade semantics and a migration
dependency across the boundary — and the module can never be lifted out
again. Cross-module references are plain integer ids instead.

Run:  python ops/checks/no_cross_module_fk.py
"""
import os
import pathlib
import sys

# Runnable from anywhere: put the repo root on sys.path before importing config.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import django

ALLOWED_TARGETS = {"core", "contenttypes", "auth"}


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()
    from django.apps import apps

    violations = []
    for model in apps.get_models():
        src = model._meta.app_label
        for f in model._meta.get_fields():
            if not getattr(f, "is_relation", False) or f.related_model is None:
                continue
            if not getattr(f, "concrete", False):
                continue                       # reverse accessor, not a real column
            dst = f.related_model._meta.app_label
            if dst != src and dst not in ALLOWED_TARGETS:
                violations.append(f"{src}.{model.__name__}.{f.name} -> {dst}")

    for v in violations:
        print(f"cross-module FK: {v}", file=sys.stderr)
    if violations:
        print(f"\n{len(violations)} cross-module foreign key(s). "
              f"Use a plain id column and read via contracts.py.", file=sys.stderr)
        return 1
    print("no cross-module foreign keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
