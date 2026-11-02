import unittest
from datetime import date
from decimal import Decimal
from modules.visitor_hostel.domain.cancellation_policy import calculate_cancellation_charge, calculate_refund_amount

class TestCancellationPolicy(unittest.TestCase):
    def test_cancellation_seven_or_more_days_free(self):
        arrival = date(2026, 6, 10)
        cancel = [date(2026, 6, 2), date(2026, 6, 3)]
        self.assertEqual(calculate_cancellation_charge(arrival, cancel[0]), Decimal("0.00"))
        self.assertEqual(calculate_cancellation_charge(arrival, cancel[1]), Decimal("0.00"))

    def test_cancellation_one_to_six_days_penalty(self):
        arrival = date(2026, 6, 10)
        cancel = [date(2026, 6, 6)]
        rent = Decimal("1000.00")
        self.assertEqual(calculate_cancellation_charge(arrival, cancel[0], rent), Decimal("250.00"))

    def test_cancellation_same_day_penalty(self):
        arrival = date(2026, 6, 10)
        cancel = [date(2026, 6, 10)]
        rent = Decimal("1000.00")
        self.assertEqual(calculate_cancellation_charge(arrival, cancel[0], rent), Decimal("500.00"))

    def test_cancellation_no_show_penalty(self):
        arrival = date(2026, 6, 10)
        cancel = [date(2026, 6, 11)]
        rent = Decimal("1000.00")
        self.assertEqual(calculate_cancellation_charge(arrival, cancel[0], rent), Decimal("500.00"))
        
    def test_calculate_refund(self):
        total = Decimal("1000.00")
        charge = Decimal("250.00")
        self.assertEqual(calculate_refund_amount(total, charge), Decimal("750.00"))
        
        total = Decimal("100.00")
        charge = Decimal("250.00")
        self.assertEqual(calculate_refund_amount(total, charge), Decimal("0.00"))
