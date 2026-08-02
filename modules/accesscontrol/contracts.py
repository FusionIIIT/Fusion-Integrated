"""accesscontrol's public surface."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from modules.accesscontrol.models import Module


def build_navigation(*, granted_module_codes: Sequence[str],
                     permissions: Iterable[str]) -> list[dict]:
    """Navigation, already filtered and already in render shape.

    The client does zero filtering — it cannot draw a module the server did not
    send. Compare the legacy client, which kept a hardcoded array whose ids had
    to exactly match database COLUMN names.
    """
    perms = set(permissions)
    granted = set(granted_module_codes)
    if not granted:
        return []

    sections: dict[str, list[dict]] = {}
    modules = (Module.objects.filter(code__in=granted, status="active")
               .prefetch_related("nav_items"))

    for m in modules:
        items = [
            {"code": n.code, "label": n.label, "icon": n.icon, "to": n.to}
            for n in m.nav_items.all()
            if not n.required_permission or n.required_permission in perms
        ]
        if not items:
            continue                     # a section that expands to nothing is worse
                                         # than no section at all
        entry = {"code": m.code, "label": m.label, "icon": m.icon}
        if len(items) == 1 and items[0]["to"] == m.base_path:
            entry["to"] = items[0]["to"]     # single link — no pointless accordion
        else:
            entry["links"] = items
        sections.setdefault(m.nav_section, []).append(entry)

    return [{"section": s, "items": v} for s, v in sections.items()]


def active_module_codes() -> list[str]:
    return list(Module.objects.filter(status="active").values_list("code", flat=True))
