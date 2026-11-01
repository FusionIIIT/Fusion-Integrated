#!/usr/bin/env python
"""Every server-side nav item must have a client route, and vice versa.

The sidebar is built on the server (ADR-0010) and the routes live in the
client, with nothing linking the two at compile time. Drift is invisible in
review and obvious to a user: a dead link, or a page nobody can reach.
"""
from __future__ import annotations

import importlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Routes that exist deliberately without a nav entry.
EXEMPT_ROUTES = {
    "",           # the index redirect
}


def client_routes(module: str) -> set[str]:
    path = ROOT / "client" / "src" / "modules" / module / "routes.tsx"
    if not path.exists():
        return set()
    src = path.read_text()
    return {m.group(1) for m in re.finditer(r'\{\s*path:\s*"([^"]+)"', src)}


def main() -> int:
    import os

    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()

    from django.conf import settings

    problems: list[str] = []
    for dotted in settings.DOMAIN_MODULES:
        name = dotted.rsplit(".", 1)[-1]
        try:
            registry = importlib.import_module(f"{dotted}.registry")
        except ModuleNotFoundError:
            continue

        base = registry.MODULE["base_path"].rstrip("/")
        nav_paths = set()
        for item in registry.NAV_ITEMS:
            to = item["to"]
            if not to.startswith(base):
                problems.append(
                    f"{name}: nav item {item['code']!r} points at {to!r}, which "
                    f"is outside the module's base path {base!r}")
                continue
            nav_paths.add(to[len(base):].lstrip("/"))

        routes = client_routes(name) | EXEMPT_ROUTES

        problems.extend(
            f"{name}: the sidebar links to {base}/{missing} but the client "
            f"has no route for it — the link would go nowhere"
            for missing in sorted(nav_paths - routes))
        problems.extend(
            f"{name}: the client has a route {base}/{orphan} with no nav "
            f"item — the page is unreachable from the sidebar"
            for orphan in sorted(routes - nav_paths - EXEMPT_ROUTES))

        # A nav item guarded by an unholdable permission is invisible forever.
        known = {code for code, _ in getattr(registry, "PERMISSIONS", [])}
        if known:
            for item in registry.NAV_ITEMS:
                perm = item.get("required_permission")
                if perm and perm not in known:
                    problems.append(
                        f"{name}: nav item {item['code']!r} requires {perm!r}, "
                        f"which is not in the module's PERMISSIONS list")

    if problems:
        print("navigation and routes disagree:\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("nav items and client routes agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
