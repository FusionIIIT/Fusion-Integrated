"""Test that no ForeignKeys in ELM cross module boundaries (ADR-0004).

Enforces Rule 2: Cross-module references must be plain integer IDs.
"""
import ast
import pathlib
import unittest


class TestNoCrossModuleFk(unittest.TestCase):

    def test_no_foreign_key_crosses_module_boundary(self):
        models_file = pathlib.Path(__file__).resolve().parents[1] / "models.py"
        self.assertTrue(models_file.exists())

        tree = ast.parse(models_file.read_text())
        allowed_targets = {"LeaveType", "LeaveApplication"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id

                if func_name == "ForeignKey":
                    # First argument is target model
                    first_arg = node.args[0]
                    target_name = ""
                    if isinstance(first_arg, ast.Name):
                        target_name = first_arg.id
                    elif isinstance(first_arg, ast.Constant):
                        target_name = str(first_arg.value)

                    self.assertIn(
                        target_name,
                        allowed_targets,
                        f"Forbidden cross-module ForeignKey to {target_name} in ELM models!",
                    )


if __name__ == "__main__":
    unittest.main()
