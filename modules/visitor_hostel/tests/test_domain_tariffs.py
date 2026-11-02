import unittest
from datetime import date
from decimal import Decimal
from modules.visitor_hostel.domain.tariff_policy import get_applicable_tariff, calculate_room_charge, TariffNotFoundError

class TestTariffPolicy(unittest.TestCase):
    def setUp(self):
        self.tariff_entries = [
            {"category": "A", "room_type": "Single", "effective_from": date(2025, 1, 1), "rate": Decimal("500.00")},
            {"category": "A", "room_type": "Single", "effective_from": date(2026, 1, 1), "rate": Decimal("600.00")},
            {"category": "B", "room_type": "Double", "effective_from": date(2026, 1, 1), "rate": Decimal("800.00")},
        ]

    def test_tariff_resolution_effective_date(self):
        self.assertEqual(get_applicable_tariff('A', 'Single', date(2026, 6, 1), self.tariff_entries), Decimal("600.00"))
        self.assertEqual(get_applicable_tariff('A', 'Single', date(2025, 6, 1), self.tariff_entries), Decimal("500.00"))
        
    def test_tariff_not_found(self):
        with self.assertRaises(TariffNotFoundError):
            get_applicable_tariff('D', 'Single', date(2026, 1, 1), self.tariff_entries)
            
    def test_room_charge_calculation(self):
        rate = Decimal("600.00")
        start_date = date(2026, 6, 1)
        end_date = date(2026, 6, 4)
        num_rooms = 2
        
        self.assertEqual(calculate_room_charge(rate, start_date, end_date, num_rooms), Decimal("3600.00"))
