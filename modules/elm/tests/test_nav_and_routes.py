"""Test that all ELM server nav items correspond to client routes and vice versa.

Guarantees no dead sidebar links or unreachable client routes (ADR-0010).
"""
import pathlib
import re
import unittest

from modules.elm.registry import MODULE, NAV_ITEMS, PERMISSIONS


class TestElmNavAndRoutes(unittest.TestCase):

    def test_nav_paths_match_client_routes(self):
        root = pathlib.Path(__file__).resolve().parents[3]
        routes_file = root / "client" / "src" / "modules" / "elm" / "routes.tsx"
        self.assertTrue(routes_file.exists(), f"Missing routes file at {routes_file}")

        src = routes_file.read_text()
        routes = {m.group(1) for m in re.finditer(r'\{\s*path:\s*"([^"]+)"', src)}

        base = MODULE["base_path"].rstrip("/")  # "/leave"
        nav_subpaths = set()
        for item in NAV_ITEMS:
            to = item["to"]
            self.assertTrue(
                to.startswith(base),
                f"Nav item {item['code']} points to {to}, which is outside base {base}",
            )
            nav_subpaths.add(to[len(base):].lstrip("/"))

        # Every nav item must have a client route
        missing_routes = nav_subpaths - routes
        self.assertEqual(
            missing_routes,
            set(),
            f"The sidebar links to {missing_routes} but the client has no route for it!",
        )

        # Every client route must have a nav item (or be exempt)
        orphan_routes = routes - nav_subpaths
        self.assertEqual(
            orphan_routes,
            set(),
            f"The client has routes {orphan_routes} with no nav item in registry.py!",
        )

    def test_all_nav_items_use_declared_permissions(self):
        """Every nav item's required_permission must be declared in PERMISSIONS."""
        known_perms = {p[0] for p in PERMISSIONS}
        for item in NAV_ITEMS:
            perm = item.get("required_permission")
            if perm:
                self.assertIn(
                    perm,
                    known_perms,
                    f"Nav item {item['code']} requires undeclared permission {perm}",
                )


if __name__ == "__main__":
    unittest.main()
