"""Merges what every `modules/vms/jobs/*.py` declares (TASK_ROUTES, BEAT_SCHEDULE).

No lane edits this file. A jobs module must be importable before Django apps
are ready (config/celery.py imports this), so it declares the two dicts and
keeps model imports inside the task bodies, like placement/tasks.py.
"""
from __future__ import annotations

import importlib
import pkgutil

from modules.vms import jobs


def job_modules() -> list:
    return [importlib.import_module(f"{jobs.__name__}.{m.name}")
            for m in sorted(pkgutil.iter_modules(jobs.__path__), key=lambda m: m.name)
            if not m.name.startswith("_")]


def merge(mods) -> tuple[dict, dict]:
    routes: dict = {}
    beat: dict = {}
    for mod in mods:
        for target, attr in ((routes, "TASK_ROUTES"), (beat, "BEAT_SCHEDULE")):
            for key, value in getattr(mod, attr, {}).items():
                if key in target:
                    raise RuntimeError(f"{mod.__name__}: duplicate {attr} key {key!r}")
                target[key] = value
    return routes, beat


TASK_ROUTES, BEAT_SCHEDULE = merge(job_modules())
