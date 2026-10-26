"""Test that modules/elm/domain/ remains pure Python with NO framework imports.

Enforces Rule 3 of Fusion ERP architecture (ADR-0003).
"""
import ast
import pathlib
import unittest

FORBIDDEN = {"django", "rest_framework", "celery"}


class TestDomainPurity(unittest.TestCase):

    def test_domain_has_zero_forbidden_imports(self):
        domain_dir = pathlib.Path(__file__).resolve().parents[1] / "domain"
        self.assertTrue(domain_dir.exists())

        for py_file in domain_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertNotIn(
                            top,
                            FORBIDDEN,
                            f"{py_file.name} directly imports forbidden package '{top}'!",
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top = node.module.split(".")[0]
                        self.assertNotIn(
                            top,
                            FORBIDDEN,
                            f"{py_file.name} imports from forbidden package '{top}'!",
                        )


if __name__ == "__main__":
    unittest.main()
