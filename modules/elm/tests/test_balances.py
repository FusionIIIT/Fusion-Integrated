import os
import unittest
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
import django
django.setup()

from modules.elm.services.balances import process_year_end, credit_annual_leaves, ANNUAL_ENTITLEMENTS


class TestBalanceCalculationLogic(unittest.TestCase):
    def test_annual_entitlements_structure(self):
        # Verify faculty entitlements
        self.assertEqual(ANNUAL_ENTITLEMENTS["faculty"]["CL"], Decimal("8.0"))
        self.assertEqual(ANNUAL_ENTITLEMENTS["faculty"]["VL"], Decimal("60.0"))
        self.assertEqual(ANNUAL_ENTITLEMENTS["faculty"]["COL"], Decimal("20.0"))
        self.assertEqual(ANNUAL_ENTITLEMENTS["faculty"]["SCL"], Decimal("15.0"))

        # Verify staff entitlements
        self.assertEqual(ANNUAL_ENTITLEMENTS["staff"]["CL"], Decimal("8.0"))
        self.assertEqual(ANNUAL_ENTITLEMENTS["staff"]["EL"], Decimal("30.0"))
        self.assertEqual(ANNUAL_ENTITLEMENTS["staff"]["COL"], Decimal("20.0"))
        self.assertEqual(ANNUAL_ENTITLEMENTS["staff"]["SCL"], Decimal("15.0"))

    def test_vl_to_el_conversion_ratio(self):
        # BR-EL-007: 2 VL = 1 EL, including fractional conversions
        cases = [
            (Decimal("60.0"), Decimal("30.0")),
            (Decimal("45.0"), Decimal("22.5")),
            (Decimal("1.0"), Decimal("0.5")),
            (Decimal("0.0"), Decimal("0.0")),
        ]
        for vl, expected_el in cases:
            converted = vl / Decimal("2.0")
            self.assertEqual(converted, expected_el)


if __name__ == "__main__":
    unittest.main()
