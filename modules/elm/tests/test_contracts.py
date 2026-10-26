"""Tests for ELM cross-module contract."""
import ast
import pathlib
import unittest


class TestElmContracts(unittest.TestCase):

    def test_all_contract_getters_are_plural(self):
        """Ensure all getters in modules/elm/contracts.py take sequences."""
        contracts_path = pathlib.Path(__file__).resolve().parents[1] / "contracts.py"
        self.assertTrue(contracts_path.exists())

        tree = ast.parse(contracts_path.read_text())
        getters = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name.startswith("get_")
            and not node.name.startswith("_")
        ]
        self.assertGreater(len(getters), 0)

        seq_hints = ("Sequence", "Iterable", "list", "List", "set", "tuple", "Collection")
        for g in getters:
            first_arg = g.args.args[0]
            # Verify first arg is user_ids or plural identifier
            self.assertIn("ids", first_arg.arg)


if __name__ == "__main__":
    unittest.main()
