"""The structural guarantee behind Phase 1 of ADR-0014.

Serving a request must not require the ERP. That is a property of the import
graph rather than of any one function, so it is checked statically — nobody
should be expected to notice a new helper in views/ pulling in an ERP model
three call frames down.
"""
import ast
import pathlib

from django.test import SimpleTestCase

IAM = pathlib.Path(__file__).resolve().parent.parent

# Anything that reaches the ERP. api.models.erp holds the managed=False shadows.
ERP_MODULES = ("iam.erp_source", "api.models.erp", "api.models")


def imported_modules(path: pathlib.Path) -> set[str]:
    """Every module named by an import in this file, including inside
    functions — a deferred import is still a dependency."""
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{a.name}" for a in node.names)
    return found


def touches_erp(path: pathlib.Path) -> set[str]:
    return {m for m in imported_modules(path)
            if any(m == e or m.startswith(e + ".") for e in ERP_MODULES)}


class ErpIsolationTests(SimpleTestCase):

    def test_no_view_imports_the_erp(self):
        offenders = {
            p.relative_to(IAM).as_posix(): sorted(touches_erp(p))
            for p in (IAM / "views").rglob("*.py") if touches_erp(p)
        }
        self.assertEqual(offenders, {},
                         "A view reached for the ERP. Requests must be served "
                         "from the projection — see ADR-0014.")

    def test_services_does_not_import_the_erp_at_module_level(self):
        """services.py may reach the ERP only through the documented login
        fallback, which imports iam.sync lazily inside _verify(). A top-level
        import would mean the module cannot even load without the ERP."""
        tree = ast.parse((IAM / "services.py").read_text())
        top_level = set()
        for node in tree.body:                        # module level only
            if isinstance(node, ast.Import):
                top_level.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_level.add(node.module)
        self.assertEqual(
            {m for m in top_level
             if any(m == e or m.startswith(e + ".") for e in ERP_MODULES)},
            set())

    def test_sync_is_the_only_importer_of_erp_source(self):
        """One doorway. If a second module opens one, the boundary is no longer
        a boundary and nobody will notice until the ERP is down."""
        importers = sorted(
            p.relative_to(IAM).as_posix()
            for p in IAM.rglob("*.py")
            if p.name != "erp_source.py"
            and not p.as_posix().startswith((IAM / "tests").as_posix())
            and "iam.erp_source" in imported_modules(p)
        )
        self.assertEqual(importers, ["sync.py"])

    def test_erp_source_is_not_imported_by_authentication(self):
        self.assertEqual(touches_erp(IAM / "authentication.py"), set())

    def test_the_url_conf_reaches_no_erp_module(self):
        self.assertEqual(touches_erp(IAM / "urls.py"), set())
