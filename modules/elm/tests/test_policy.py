import unittest
from decimal import Decimal

from modules.elm.domain.errors import (
    ELMDomainError,
    InsufficientBalanceError,
)
from modules.elm.domain.policy import validate_sufficient_balance


class TestValidateSufficientBalance(unittest.TestCase):
    def test_sufficient_integer_balance(self):
        self.assertIsNone(validate_sufficient_balance(10, 8))

    def test_exact_balance_is_sufficient(self):
        self.assertIsNone(validate_sufficient_balance(5, 5))

    def test_half_day_quantities(self):
        self.assertIsNone(
            validate_sufficient_balance(Decimal("1.5"), Decimal("0.5"))
        )

    def test_insufficient_balance_raises_domain_error(self):
        with self.assertRaises(InsufficientBalanceError) as caught:
            validate_sufficient_balance(Decimal("1.5"), Decimal("2.0"))

        self.assertIsInstance(caught.exception, ELMDomainError)
        self.assertEqual(caught.exception.balance, Decimal("1.5"))
        self.assertEqual(caught.exception.required, Decimal("2.0"))

    def test_negative_values_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_sufficient_balance(-1, 0)

        with self.assertRaises(ValueError):
            validate_sufficient_balance(1, Decimal("-0.5"))

    def test_invalid_types_are_rejected(self):
        for value in (True, 1.5, "2", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    validate_sufficient_balance(value, 1)

        for value in (False, 0.5, "1", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    validate_sufficient_balance(1, value)

    def test_non_finite_decimal_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sufficient_balance(Decimal("NaN"), 1)

        with self.assertRaises(ValueError):
            validate_sufficient_balance(1, Decimal("Infinity"))


if __name__ == "__main__":
    unittest.main()
